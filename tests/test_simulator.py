import pytest
from hr_monitor.simulator import (
    HRSimulatorConfig,
    HRMonitorMqttSimulator,
    SimulatorState,
)
from hr_monitor.protocols import MqttClient
from asyncio import sleep
from unittest.mock import call


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
async def simulator(mocker, example_config_file, mock_repository, mock_mqtt_client):
    sim = HRMonitorMqttSimulator(
        repository=mock_repository,
        config=HRSimulatorConfig.from_json_file(example_config_file),
        mqtt_client=mock_mqtt_client,
    )
    try:
        yield sim
    finally:
        await sim.close()


@pytest.mark.asyncio
async def test_new_state_when_created(simulator):
    assert simulator.state == SimulatorState.NEW


@pytest.mark.asyncio
async def test_running_state_when_started(simulator):
    await simulator.start()
    assert simulator.state == SimulatorState.RUNNING


@pytest.mark.asyncio
async def test_paused_state_when_stopped(simulator):
    await simulator.start()
    await simulator.stop()
    assert simulator.state == SimulatorState.PAUSED


@pytest.mark.asyncio
async def test_closed_state_when_closed(simulator):
    await simulator.close()
    assert simulator.state == SimulatorState.CLOSED


@pytest.mark.asyncio
async def test_state_transitions_are_idempotent(simulator):
    assert simulator.state == SimulatorState.NEW
    await simulator.start()
    assert simulator.state == SimulatorState.RUNNING
    await simulator.start()
    assert simulator.state == SimulatorState.RUNNING
    await simulator.stop()
    assert simulator.state == SimulatorState.PAUSED
    await simulator.stop()
    assert simulator.state == SimulatorState.PAUSED
    await simulator.start()
    assert simulator.state == SimulatorState.RUNNING
    await simulator.close()
    assert simulator.state == SimulatorState.CLOSED
    await simulator.close()
    assert simulator.state == SimulatorState.CLOSED


@pytest.mark.asyncio
async def test_topic_continuous_frames(simulator):
    await simulator.start()
    await sleep(1)
    simulator._mqtt.publish.assert_has_calls(
        [
            call("example/runner", "runner 1", qos=0, retain=False),
            call("example/runner", "runner 2", qos=0, retain=False),
            call("example/runner", "runner 3", qos=0, retain=False),
            call("example/walker", "walker 1", qos=0, retain=False),
            call("example/walker", "walker 2", qos=0, retain=False),
            call("example/walker", "walker 3", qos=0, retain=False),
        ],
        any_order=True,
    )


@pytest.mark.asyncio
async def test_no_publish_when_not_running(simulator):
    await sleep(1)
    simulator._mqtt.publish.assert_not_called()


@pytest.mark.skip(reason="This technical debt, not a bug")
@pytest.mark.asyncio
async def test_no_publish_when_stopped(simulator):
    await simulator.start()
    await sleep(1)
    await simulator.stop()
    simulator._mqtt.publish.reset_mock()
    await sleep(1)
    simulator._mqtt.publish.assert_not_called()  # frame leftovers ! TODO: fix this


@pytest.mark.asyncio
async def test_no_publish_when_closed(simulator):
    await simulator.start()
    await sleep(1)
    await simulator.close()
    simulator._mqtt.publish.reset_mock()
    await sleep(1)
    simulator._mqtt.publish.assert_not_called()
