import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_monitor.exceptions import (
    DeviceInitializationError,
    HRMonitorException,
    HRVCalculationError,
    InvalidConfigurationError,
    InvalidPayloadTypeError,
    MQTTConnectionError,
    SimulatorError,
)
from rest.error_handlers import register_exception_handlers
from rest.exceptions import (
    InvalidConfigurationError as ServiceConfigurationError,
    SimulationServiceException,
)
from rr_repository.exceptions import (
    InitializationError,
    RecordDuplicateError,
    RecordNotFoundError,
    RecordValidationError,
    RRRepositoryException,
)

SECRET = "/secret/path broker.internal:1883"

CASES = [
    # exception, status, expected detail (None = must equal str(exc))
    (RecordNotFoundError("t1"), 404, None),
    (RecordDuplicateError("t1"), 409, None),
    (RecordValidationError("bad"), 422, None),
    (MQTTConnectionError(OSError(SECRET)), 503, "MQTT broker unavailable"),
    (InitializationError(SECRET), 503, "Record repository unavailable"),
    (InvalidConfigurationError(SECRET), 500, "Simulator configuration is invalid"),
    (DeviceInitializationError(SECRET), 500, "Simulator configuration is invalid"),
    (HRVCalculationError(SECRET), 500, "Internal server error"),
    (InvalidPayloadTypeError(SECRET), 500, "Internal server error"),
    (HRMonitorException(SECRET), 500, "Internal server error"),
    (RRRepositoryException(SECRET), 500, "Internal server error"),
    (SimulationServiceException(SECRET), 500, "Internal server error"),
    (ServiceConfigurationError(SECRET), 500, "Internal server error"),
    (RuntimeError(SECRET), 500, "Internal server error"),
    (ConnectionError(SECRET), 500, "Internal server error"),
]


def _client_raising(exc: Exception) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise exc

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("exc,status,detail", CASES, ids=lambda v: type(v).__name__)
def test_exception_maps_to_status_and_json_shape(exc, status, detail):
    response = _client_raising(exc).get("/boom")

    assert response.status_code == status
    assert response.json() == {"detail": detail if detail is not None else str(exc)}


@pytest.mark.parametrize(
    "exc", [c[0] for c in CASES if c[1] >= 500], ids=lambda v: type(v).__name__
)
def test_server_errors_do_not_leak_internals(exc):
    response = _client_raising(exc).get("/boom")

    assert "secret" not in response.text
    assert "broker.internal" not in response.text


def test_simulator_error_keeps_last_error():
    response = _client_raising(SimulatorError(ValueError("x"))).get("/boom")

    assert response.status_code == 409
    assert response.json()["last_error"] == "ValueError('x')"
