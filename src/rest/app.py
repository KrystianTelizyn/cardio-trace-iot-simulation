from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from hr_monitor import HRSimulatorConfig, HRMonitorMqttSimulator
from hr_monitor.adapters import AioMqttClientAdapter
from hr_monitor.exceptions import HRMonitorException, SimulatorError
from rr_repository import RecordRepository
from rr_repository.exceptions import RRRepositoryException
from .routes import router
from dotenv import load_dotenv
from .exceptions import InvalidConfigurationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    # Initialise the simulator from environment variables.
    config_path = os.getenv("SIM_CONFIG_PATH")
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    db_path = os.getenv("RR_DB_PATH")

    try:
        simulation_config = HRSimulatorConfig.from_json_file(config_path)
        repository = RecordRepository(db_path)
        mqtt_client = AioMqttClientAdapter(hostname=mqtt_host, port=mqtt_port)

        simulator = HRMonitorMqttSimulator(
            repository=repository,
            config=simulation_config,
            mqtt_client=mqtt_client,
        )

    except (HRMonitorException, RRRepositoryException) as e:
        raise InvalidConfigurationError(
            f"Failed to initialize simulator service: {e}"
        ) from e

    app.state.simulator = simulator
    app.state.config_path = config_path
    yield
    await simulator.stop()


app = FastAPI(title="Cardio Trace Simulator API", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(SimulatorError)
async def simulator_error_handler(
    request: Request, exc: SimulatorError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "last_error": repr(exc.last_error),
        },
    )


@app.exception_handler(HRMonitorException)
async def general_simulator_error_handler(
    request: Request, exc: HRMonitorException
) -> JSONResponse:
    # Convert uncaught Exceptions into a stable API response shape.
    return JSONResponse(
        status_code=500,
        content={"detail": exc.message},
    )
