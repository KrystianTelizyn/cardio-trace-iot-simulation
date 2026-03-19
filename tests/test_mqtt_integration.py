import pytest
from itertools import chain
from hr_monitor import HRMonitorMqttSimulator, HRSimulatorConfig
from hr_monitor.adapters import AioMqttClientAdapter


@pytest.fixture
async def mqtt_client_adapter(mosquitto_broker):
    host, port = mosquitto_broker
    client = AioMqttClientAdapter(hostname=host, port=port)
    yield client
    await client.disconnect()


@pytest.fixture
async def simulator_with_mqtt(
    mqtt_client_adapter, example_config_file, mock_repository
):
    simulator = HRMonitorMqttSimulator(
        config=HRSimulatorConfig.from_json_file(example_config_file),
        mqtt_client=mqtt_client_adapter,
        repository=mock_repository,
    )
    try:
        yield simulator
    finally:
        await simulator.close()


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_mqtt_integration_runner(simulator_with_mqtt, mqtt_client):
    await mqtt_client.subscribe("example/runner")
    await simulator_with_mqtt.start()
    # obtain first 5 messages
    messages = []
    async for message in mqtt_client.messages:
        messages.append(message)
        if len(messages) >= 5:
            break
    await simulator_with_mqtt.stop()
    for i, message in enumerate(messages):
        assert message.payload.decode("utf-8") == f"runner {i + 1}"


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_mqtt_integration_walker(simulator_with_mqtt, mqtt_client):
    await mqtt_client.subscribe("example/walker")
    await simulator_with_mqtt.start()
    # obtain first 5 messages
    messages = []
    async for message in mqtt_client.messages:
        messages.append(message)
        if len(messages) >= 5:
            break
    await simulator_with_mqtt.stop()
    for i, message in enumerate(messages):
        assert message.payload.decode("utf-8") == f"walker {i + 1}"


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_mqtt_integration_walker_runner(simulator_with_mqtt, mqtt_client):
    await mqtt_client.subscribe("example/#")
    await simulator_with_mqtt.start()
    # obtain first 10 messages
    messages = {"example/runner": [], "example/walker": []}
    async for message in mqtt_client.messages:
        messages[message.topic.value].append(message)
        # check if we have 10 messages
        if len(list(chain(*messages.values()))) >= 10:
            break
    await simulator_with_mqtt.stop()
    for i, message in enumerate(messages["example/walker"]):
        assert message.payload.decode("utf-8") == f"walker {i + 1}"
    for i, message in enumerate(messages["example/runner"]):
        assert message.payload.decode("utf-8") == f"runner {i + 1}"
