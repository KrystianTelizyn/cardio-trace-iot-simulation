"""Maps domain exceptions to HTTP responses with one JSON shape: {"detail": ...}.

Policy:
- 4xx (client-correctable): detail is the exception message.
- 5xx: detail is a fixed public message. The real exception is logged, never
  returned, so hostnames, file paths and driver errors do not leak.
- Lookup follows the exception's MRO, so the most specific registration wins
  and the base classes / Exception act as fallbacks.
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hr_monitor.exceptions import (
    DeviceInitializationError,
    HRMonitorException,
    HRVCalculationError,
    InvalidPayloadTypeError,
    MQTTConnectionError,
    SimulatorError,
)
from hr_monitor.exceptions import InvalidConfigurationError as SimulatorConfigError
from rr_repository.exceptions import (
    InitializationError,
    RecordDuplicateError,
    RecordNotFoundError,
    RecordValidationError,
    RRRepositoryException,
)

from .exceptions import SimulationServiceException

logger = logging.getLogger(__name__)

INTERNAL_ERROR = "Internal server error"

# exception class -> (status code, public detail; None = use str(exc), 4xx only)
ERROR_MAP: dict[type[Exception], tuple[int, Optional[str]]] = {
    # client-correctable
    RecordNotFoundError: (404, None),
    RecordDuplicateError: (409, None),
    RecordValidationError: (422, None),
    # dependency unavailable
    MQTTConnectionError: (503, "MQTT broker unavailable"),
    InitializationError: (503, "Record repository unavailable"),
    # server-side misconfiguration / bugs
    SimulatorConfigError: (500, "Simulator configuration is invalid"),
    DeviceInitializationError: (500, "Simulator configuration is invalid"),
    HRVCalculationError: (500, INTERNAL_ERROR),
    InvalidPayloadTypeError: (500, INTERNAL_ERROR),
    # fallbacks for anything else we own
    HRMonitorException: (500, INTERNAL_ERROR),
    RRRepositoryException: (500, INTERNAL_ERROR),
    SimulationServiceException: (500, INTERNAL_ERROR),
    # anything not ours (aiomqtt, sqlalchemy, bugs)
    Exception: (500, INTERNAL_ERROR),
}


def _make_handler(status_code: int, public_detail: Optional[str]):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        if status_code >= 500:
            logger.error(
                "%s %s failed: %r",
                request.method,
                request.url.path,
                exc,
                exc_info=exc,
            )
        detail = public_detail if public_detail is not None else str(exc)
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return handler


async def simulator_error_handler(request: Request, exc: SimulatorError):
    """409: simulator is in ERROR state; carries the underlying device error."""
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "last_error": repr(exc.last_error)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    for exc_class, (status_code, public_detail) in ERROR_MAP.items():
        app.add_exception_handler(exc_class, _make_handler(status_code, public_detail))
    app.add_exception_handler(SimulatorError, simulator_error_handler)
