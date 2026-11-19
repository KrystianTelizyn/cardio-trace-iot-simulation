import pytest
import json
from hr_monitor.formats import PayloadTemplates
from hr_monitor.protocols import MqttClient
from hr_monitor.simulator import HRMonitorMqttSimulator
from hr_monitor.config import HRSimulatorConfig, HRDeviceConfig
from testcontainers.core.container import DockerContainer
from aiomqtt import Client
from asyncio import sleep


@pytest.fixture
def simulated_cached_payloads(monkeypatch):
    fake_cache = {
        PayloadTemplates.Apple: "foo",
        PayloadTemplates.EHR: "bar",
        PayloadTemplates.Garmin: "baz",
    }
    monkeypatch.setattr("hr_monitor.formats._cached_payloads", fake_cache)
    return fake_cache


@pytest.fixture
def example_config():
    config_dict = {
        "devices": [
            {
                "device_id": "runner",
                "payload_format": "<device_id> <frame>",
                "topic": "example/runner",
                "hr_frame": 2,
                "hrv_frame": 9,
                "record_tag": "patient-xyz",
            },
            {
                "device_id": "walker",
                "payload_format": "<device_id> <frame>",
                "topic": "example/walker",
                "hr_frame": 2,
                "hrv_frame": 9,
                "record_tag": "patient-abc",
            },
        ],
        "qos": 0,
        "retain": False,
    }
    return json.dumps(config_dict)


@pytest.fixture
def expected_devices_list():
    return [
        HRDeviceConfig(
            device_id="runner",
            payload_format="<device_id> <frame>",
            topic="example/runner",
            hr_frame=2,
            hrv_frame=9,
            record_tag="patient-xyz",
        ),
        HRDeviceConfig(
            device_id="walker",
            payload_format="<device_id> <frame>",
            topic="example/walker",
            hr_frame=2,
            hrv_frame=9,
            record_tag="patient-abc",
        ),
    ]


@pytest.fixture
def example_config_file():
    return "tests/example_config.json"


@pytest.fixture
def mock_repository(mocker):
    mock_repository = mocker.Mock()
    mock_repository.get_record_data.return_value = [1, 2, 3, 4, 5]
    return mock_repository


@pytest.fixture
def mock_mqtt_client(mocker):
    mock_mqtt_client = mocker.AsyncMock(spec=MqttClient)
    return mock_mqtt_client


@pytest.fixture
async def simulator_mqtt_mock(
    mocker, example_config_file, mock_repository, mock_mqtt_client
):
    sim = HRMonitorMqttSimulator(
        repository=mock_repository,
        config=HRSimulatorConfig.from_json_file(example_config_file),
        mqtt_client=mock_mqtt_client,
    )
    try:
        yield sim
    finally:
        await sim.stop()


@pytest.fixture
async def mosquitto_container():
    # Function scope: every test gets its own broker, so a test may stop it.
    # To stop it mid-test use container.get_wrapped_container().stop() so the
    # context manager can still remove the container on teardown.
    with DockerContainer("eclipse-mosquitto:latest").with_exposed_ports(
        1883
    ) as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(1883))
        # retry connect with backoff
        for i in range(6):
            try:
                print(
                    f"Attempt {i + 1} to connect to mosquitto broker at {host}:{port}..."
                )
                async with Client(hostname=host, port=port, timeout=5):
                    print(f"Connected to mosquitto broker at {host}:{port}")
                break
            except Exception as e:
                print(f"Failed to connect to mosquitto broker at {host}:{port}: {e}")
                if i == 5:
                    raise RuntimeError("Failed to connect to mosquitto broker") from e
                await sleep(2**i)
        yield container


@pytest.fixture
async def mosquitto_broker(mosquitto_container):
    return (
        mosquitto_container.get_container_host_ip(),
        int(mosquitto_container.get_exposed_port(1883)),
    )


@pytest.fixture
async def mqtt_client(mosquitto_broker):
    host, port = mosquitto_broker
    async with Client(hostname=host, port=port, timeout=20) as client:
        yield client
