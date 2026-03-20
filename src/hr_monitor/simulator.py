import asyncio
import logging
from dataclasses import asdict
from enum import Enum

from hr_monitor.device import HRMonitorDevice
from hr_monitor.protocols import MqttClient, RecordRepositoryProtocol
from hr_monitor.config import HRSimulatorConfig
from hr_monitor.exceptions import (
    MQTTConnectionError,
    SimulatorError,
    InvalidConfigurationError,
)

logger = logging.getLogger(__name__)


class SimulatorState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class HRMonitorMqttSimulator:
    """Simulates multiple HRMonitorDevice instances and publishes frames over MQTT.

    - Devices are constructed eagerly in __init__ using RR intervals from RecordRepository.
    - start() begins or resumes publishing (play). If a device task failed (ERROR),
      start() raises SimulatorInErrorStateError; call stop() then start() again.
    - pause() clears the run event so device loops block (no MQTT teardown).
    - stop() performs full cleanup: cancel tasks, disconnect MQTT, clear error.
    """

    def __init__(
        self,
        repository: RecordRepositoryProtocol,
        config: HRSimulatorConfig,
        mqtt_client: MqttClient,
    ) -> None:
        self._repository = repository
        self._config = config
        self._mqtt = mqtt_client
        self._last_error: Exception | None = None
        self._run_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._devices: list[HRMonitorDevice] = []
        self._device_topics: dict[str, str] = {}

        self._build_devices()

    @property
    def state(self) -> SimulatorState:
        if self._last_error is not None:
            return SimulatorState.ERROR
        if not self._tasks:
            return SimulatorState.IDLE
        if self._run_event.is_set():
            return SimulatorState.RUNNING
        return SimulatorState.PAUSED

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    @property
    def devices_config(self) -> HRSimulatorConfig:
        return [asdict(device) for device in self._config.devices]

    def _build_devices(self) -> None:
        for dev_cfg in self._config.devices:
            try:
                rr_intervals = self._repository.get_record_data(dev_cfg.record_tag)
            except Exception as e:
                raise InvalidConfigurationError(
                    f"Failed to get record data for device {dev_cfg.device_id}"
                ) from e
            try:
                device = HRMonitorDevice(
                    device_id=dev_cfg.device_id,
                    rr_list=rr_intervals,
                    payload_format=dev_cfg.payload_format,
                    hr_frame=dev_cfg.hr_frame,
                    hrv_frame=dev_cfg.hrv_frame,
                )
            except Exception as e:
                raise InvalidConfigurationError(
                    f"Failed to initialize device {dev_cfg.device_id}"
                ) from e
            self._devices.append(device)
            self._device_topics[dev_cfg.device_id] = dev_cfg.topic

    async def start(self) -> None:
        """Start or resume simulation (play)."""
        if self.state is SimulatorState.ERROR:
            raise SimulatorError(self._last_error) from self._last_error

        if not self._tasks:
            try:
                await self._mqtt.connect()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                raise MQTTConnectionError(e) from e
            self._create_tasks()

        self._run_event.set()

    async def pause(self) -> None:
        """Pause simulation without resetting device state."""
        if self.state is SimulatorState.ERROR:
            raise SimulatorError(self._last_error) from self._last_error
        if self.state is SimulatorState.IDLE:
            return
        self._run_event.clear()

    async def stop(self) -> None:
        """Full teardown: cancel device tasks, disconnect MQTT, clear recorded error."""
        if self.state is SimulatorState.IDLE:
            return

        await self._cancel_tasks()
        try:
            await self._mqtt.disconnect()
        except Exception:
            logger.exception(
                "Failed to disconnect MQTT client while closing simulator."
            )
        self._last_error = None

    def _create_tasks(self) -> None:
        loop = asyncio.get_running_loop()
        for device in self._devices:
            topic = self._device_topics[device.device_id]
            task = loop.create_task(self._run_device_loop(device, topic))
            task.add_done_callback(self._on_device_task_done)
            self._tasks.append(task)

    async def _run_device_loop(self, device: HRMonitorDevice, topic: str) -> None:
        """Per-device loop: wait for play, then generate and publish frames."""
        logger.debug(
            "Starting device loop: device_id=%s topic=%s", device.device_id, topic
        )
        while True:
            try:
                await self._run_event.wait()
                frame = await device.obtain_next_measurement_frame()
                await self._mqtt.publish(
                    topic,
                    frame,
                    qos=self._config.qos,
                    retain=self._config.retain,
                )
            except asyncio.CancelledError:
                logger.debug(
                    "Device loop cancelled: device_id=%s topic=%s",
                    device.device_id,
                    topic,
                )
                raise
            except Exception:
                logger.exception(
                    "Device loop failed: device_id=%s topic=%s",
                    device.device_id,
                    topic,
                )
                raise

    async def _cancel_tasks(self) -> None:
        self._run_event.clear()
        for task in self._tasks:
            task.cancel()
        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.exception(
                    "Background device task ended with exception during cancellation.",
                    exc_info=result,
                )
        self._tasks.clear()

    def post_device_task_error(self, exc: Exception) -> None:
        if self.state in {SimulatorState.ERROR, SimulatorState.IDLE}:
            return
        logger.exception("Device task failed with exception.", exc_info=exc)
        self._last_error = exc
        # pause the simulator
        self._run_event.clear()

    def _on_device_task_done(self, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            self.post_device_task_error(exc)
