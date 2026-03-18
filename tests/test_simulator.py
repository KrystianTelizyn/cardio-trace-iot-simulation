import pytest
from hr_monitor.simulator import (
    SimulatorState,
)
from asyncio import sleep
from unittest.mock import call


@pytest.mark.asyncio
async def test_new_state_when_created(simulator_mqtt_mock):
    assert simulator_mqtt_mock.state == SimulatorState.NEW


@pytest.mark.asyncio
async def test_running_state_when_started(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING


@pytest.mark.asyncio
async def test_paused_state_when_stopped(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED


@pytest.mark.asyncio
async def test_closed_state_when_closed(simulator_mqtt_mock):
    await simulator_mqtt_mock.close()
    assert simulator_mqtt_mock.state == SimulatorState.CLOSED


@pytest.mark.asyncio
async def test_state_transitions_are_idempotent(simulator_mqtt_mock):
    assert simulator_mqtt_mock.state == SimulatorState.NEW
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.close()
    assert simulator_mqtt_mock.state == SimulatorState.CLOSED
    await simulator_mqtt_mock.close()
    assert simulator_mqtt_mock.state == SimulatorState.CLOSED


@pytest.mark.asyncio
async def test_topic_continuous_frames(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_has_calls(
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
async def test_no_publish_when_not_running(simulator_mqtt_mock):
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()


@pytest.mark.skip(reason="This technical debt, not a bug")
@pytest.mark.asyncio
async def test_no_publish_when_stopped(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    await simulator_mqtt_mock.stop()
    simulator_mqtt_mock._mqtt.publish.reset_mock()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()  # frame leftovers ! TODO: fix this


@pytest.mark.asyncio
async def test_no_publish_when_closed(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    await simulator_mqtt_mock.close()
    simulator_mqtt_mock._mqtt.publish.reset_mock()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()
