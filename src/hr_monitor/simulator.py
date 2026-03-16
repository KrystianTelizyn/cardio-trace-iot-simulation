from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Iterable

from hr_monitor.device import HRMonitorDevice
from hr_monitor.protocols import MqttClient, RecordRepositoryProtocol


class SimulatorState(Enum):
    NEW = auto()
    RUNNING = auto()
    PAUSED = auto()
    CLOSED = auto()


@dataclass(frozen=True)
class HRDeviceConfig:
    """Configuration for a single simulated HR monitor device."""

    device_id: str
    record_tag: str
    payload_format: str
    hr_frame: int = 5
    hrv_frame: int = 30


TopicBuilder = Callable[[str], str]


@dataclass(frozen=True)
class HRSimulatorConfig:
    """Configuration for the simulator."""

    devices: Iterable[HRDeviceConfig]
    topic_builder: TopicBuilder
    qos: int = 0
    retain: bool = False


class HRMonitorMqttSimulator:
    """Simulates multiple HRMonitorDevice instances and publishes frames over MQTT.

    - Devices are constructed eagerly in __init__ using RR intervals from RecordRepository.
    - start() begins or resumes publishing (play).
    - stop() pauses publishing without resetting device state (pause).
    - close() shuts down all tasks and disconnects MQTT (end of life).
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

        self._state: SimulatorState = SimulatorState.NEW
        self._run_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []
        self._devices: list[HRMonitorDevice] = []

        self._build_devices()

    @property
    def state(self) -> SimulatorState:
        return self._state

    def _build_devices(self) -> None:
        for dev_cfg in self._config.devices:
            rr_intervals = self._repository.get_record_data(dev_cfg.record_tag)
            device = HRMonitorDevice(
                device_id=dev_cfg.device_id,
                rr_list=rr_intervals,
                payload_format=dev_cfg.payload_format,
                hr_frame=dev_cfg.hr_frame,
                hrv_frame=dev_cfg.hrv_frame,
            )
            self._devices.append(device)

    async def start(self) -> None:
        """Start or resume simulation (play)."""
        if self._state is SimulatorState.CLOSED:
            raise RuntimeError("Simulator is closed and cannot be started.")

        if self._state is SimulatorState.NEW:
            await self._mqtt.connect()
            self._create_tasks()

        self._run_event.set()
        self._state = SimulatorState.RUNNING

    async def stop(self) -> None:
        """Pause simulation without resetting device state."""
        if self._state is SimulatorState.CLOSED:
            return
        self._run_event.clear()
        if self._state is SimulatorState.RUNNING:
            self._state = SimulatorState.PAUSED

    async def close(self) -> None:
        """Completely stop simulation and disconnect MQTT."""
        if self._state is SimulatorState.CLOSED:
            return

        self._run_event.clear()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        await self._mqtt.disconnect()
        self._state = SimulatorState.CLOSED

    def _create_tasks(self) -> None:
        loop = asyncio.get_running_loop()
        for device in self._devices:
            topic = self._config.topic_builder(device.device_id)
            task = loop.create_task(self._run_device_loop(device, topic))
            self._tasks.append(task)

    async def _run_device_loop(self, device: HRMonitorDevice, topic: str) -> None:
        """Per-device loop: wait for play, then generate and publish frames."""
        while True:
            await self._run_event.wait()
            frame = await device.obtain_next_measurement_frame()
            await self._mqtt.publish(
                topic,
                frame,
                qos=self._config.qos,
                retain=self._config.retain,
            )
