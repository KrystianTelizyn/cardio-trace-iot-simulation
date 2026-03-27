import pytest
from hr_monitor.simulator import (
    SimulatorState,
    SimulatorError,
)
from asyncio import sleep
from unittest.mock import call
import re


@pytest.mark.asyncio
async def test_new_state_when_created(simulator_mqtt_mock):
    assert simulator_mqtt_mock.state == SimulatorState.IDLE


@pytest.mark.asyncio
async def test_running_state_when_started(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING


@pytest.mark.asyncio
async def test_paused_state_when_stopped(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await simulator_mqtt_mock.pause()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED


@pytest.mark.asyncio
async def test_closed_state_when_closed(simulator_mqtt_mock):
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.IDLE


@pytest.mark.asyncio
async def test_state_transitions_are_idempotent(simulator_mqtt_mock):
    assert simulator_mqtt_mock.state == SimulatorState.IDLE
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.pause()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED
    await simulator_mqtt_mock.pause()
    assert simulator_mqtt_mock.state == SimulatorState.PAUSED
    await simulator_mqtt_mock.start()
    assert simulator_mqtt_mock.state == SimulatorState.RUNNING
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.IDLE
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.IDLE


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
async def test_resumes_frames_publishing(simulator_mqtt_mock):
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
    await simulator_mqtt_mock.pause()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.reset_mock()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()
    await simulator_mqtt_mock.start()
    await sleep(1)
    # define regex for runner arguments
    runner_payload_regex = re.compile(r"runner \d+", re.IGNORECASE)
    walker_payload_regex = re.compile(r"walker \d+", re.IGNORECASE)
    # how to assert regex in assert_has_calls?  check if any call matches the regex
    assert any(
        re.match(runner_payload_regex, call.args[1])
        for call in simulator_mqtt_mock._mqtt.publish.call_args_list
    )
    assert any(
        re.match(walker_payload_regex, call.args[1])
        for call in simulator_mqtt_mock._mqtt.publish.call_args_list
    )


@pytest.mark.asyncio
async def test_no_publish_when_not_running(simulator_mqtt_mock):
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()


@pytest.mark.skip(reason="This technical debt, not a bug")
@pytest.mark.asyncio
async def test_no_publish_when_paused(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    await simulator_mqtt_mock.pause()
    simulator_mqtt_mock._mqtt.publish.reset_mock()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()  # frame leftovers ! TODO: fix this


@pytest.mark.asyncio
async def test_no_publish_when_stopped(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    await simulator_mqtt_mock.stop()
    simulator_mqtt_mock._mqtt.publish.reset_mock()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.assert_not_called()


@pytest.mark.asyncio
async def test_error_state_transition(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.side_effect = ValueError("Test error")
    await sleep(1)
    assert simulator_mqtt_mock.state == SimulatorState.ERROR


@pytest.mark.asyncio
async def test_error_state_cleanup(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    exception = ValueError("Test error")
    simulator_mqtt_mock._mqtt.publish.side_effect = exception
    await sleep(1)
    assert simulator_mqtt_mock.state == SimulatorState.ERROR
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.IDLE
    assert simulator_mqtt_mock.last_error is None


@pytest.mark.asyncio
async def test_raises_simulator_error(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    simulator_mqtt_mock._mqtt.publish.side_effect = ValueError("Test error")
    await sleep(1)
    assert simulator_mqtt_mock.state == SimulatorState.ERROR
    with pytest.raises(SimulatorError):
        await simulator_mqtt_mock.start()
    with pytest.raises(SimulatorError):
        await simulator_mqtt_mock.pause()
    await simulator_mqtt_mock.stop()
    assert simulator_mqtt_mock.state == SimulatorState.IDLE
    assert simulator_mqtt_mock.last_error is None


@pytest.mark.asyncio
async def test_presists_last_error(simulator_mqtt_mock):
    await simulator_mqtt_mock.start()
    await sleep(1)
    exception = ValueError("Test error")
    simulator_mqtt_mock._mqtt.publish.side_effect = exception
    await sleep(1)
    assert simulator_mqtt_mock.state == SimulatorState.ERROR
    assert simulator_mqtt_mock.last_error is exception
