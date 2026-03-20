import pytest
from fastapi.testclient import TestClient
from dataclasses import asdict
import os
from asyncio import sleep
from rest.app import app
from hr_monitor.exceptions import SimulatorError


@pytest.fixture
def api_client(mocker, mock_repository, mosquitto_broker, example_config_file):
    host, port = mosquitto_broker

    mocker.patch("rest.app.RecordRepository", return_value=mock_repository)

    mocker.patch.dict(
        os.environ,
        {
            "SIM_CONFIG_PATH": example_config_file,
            "MQTT_HOST": host,
            "MQTT_PORT": str(port),
        },
    )

    with TestClient(app) as client:
        yield client


def test_health_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_devices_endpoint(api_client, expected_devices_list):
    response = api_client.get("/devices")
    assert response.status_code == 200
    body = response.json()
    assert body["devices"] == [asdict(device) for device in expected_devices_list]


def test_simulation_status_endpoint(api_client):
    response = api_client.get("/simulation/status")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "IDLE"
    assert "config_path" in body


def test_start_stop_cycle(api_client):
    start_resp = api_client.post("/simulation/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["state"] == "RUNNING"

    status_resp = api_client.get("/simulation/status")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["state"] == "RUNNING"
    assert "config_path" in status_body

    stop_resp = api_client.post("/simulation/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["state"] == "IDLE"


@pytest.mark.timeout(20)
@pytest.mark.asyncio
async def test_rest_mqtt_subscription_and_payloads(api_client, mqtt_client):
    # Subscribe before starting the simulation to avoid missing the first frames.
    await mqtt_client.subscribe("example/#")

    start_resp = api_client.post("/simulation/start")
    assert start_resp.status_code == 200

    messages = {"example/runner": [], "example/walker": []}
    expected_each = 3

    async for message in mqtt_client.messages:
        topic = message.topic.value
        if topic in messages:
            messages[topic].append(message.payload.decode("utf-8"))

        if all(len(v) >= expected_each for v in messages.values()):
            break

    # Ensure we stop the simulator after collecting payloads.
    stop_resp = api_client.post("/simulation/stop")
    assert stop_resp.status_code == 200

    for i, payload in enumerate(messages["example/runner"]):
        assert payload == f"runner {i + 1}"

    for i, payload in enumerate(messages["example/walker"]):
        assert payload == f"walker {i + 1}"


@pytest.mark.asyncio
async def test_simulation_pause_endpoint(api_client):
    start_resp = api_client.post("/simulation/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["state"] == "RUNNING"
    await sleep(1)
    response = api_client.post("/simulation/pause")
    assert response.status_code == 200
    assert response.json()["state"] == "PAUSED"
    resume_resp = api_client.post("/simulation/start")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["state"] == "RUNNING"
    await sleep(1)
    response = api_client.post("/simulation/pause")
    assert response.status_code == 200
    assert response.json()["state"] == "PAUSED"


@pytest.mark.asyncio
async def test_returns_409_when_internal_error(api_client, mocker):
    mocker.patch.object(
        app.state.simulator,
        "start",
        side_effect=SimulatorError(ValueError("Test error")),
    )
    response = api_client.post("/simulation/start")
    assert response.status_code == 409
    assert "ValueError('Test error')" in response.json()["detail"]
    assert response.json()["last_error"] == "ValueError('Test error')"
    mocker.patch.object(
        app.state.simulator,
        "pause",
        side_effect=SimulatorError(ValueError("Test error")),
    )
    response = api_client.post("/simulation/pause")
    assert response.status_code == 409
    assert "ValueError('Test error')" in response.json()["detail"]
    assert response.json()["last_error"] == "ValueError('Test error')"
