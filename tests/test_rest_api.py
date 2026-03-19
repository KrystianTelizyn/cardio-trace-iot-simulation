import pytest
from fastapi.testclient import TestClient
from dataclasses import asdict
import os


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

    from rest.app import app

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
    assert stop_resp.json()["state"] == "PAUSED"


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
