from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from hr_monitor import HRSimulatorConfig, HRMonitorMqttSimulator
from hr_monitor.adapters import AioMqttClientAdapter
from rr_repository import RecordRepository
from .routes import router
from dotenv import load_dotenv


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    # Initialise the simulator from environment variables.
    config_path = os.getenv("SIM_CONFIG_PATH")
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    db_path = os.getenv("RR_DB_PATH")

    simulator = HRMonitorMqttSimulator(
        repository=RecordRepository(db_path),
        config=HRSimulatorConfig.from_json_file(config_path),
        mqtt_client=AioMqttClientAdapter(hostname=mqtt_host, port=mqtt_port),
    )
    app.state.simulator = simulator
    yield
    await simulator.close()


app = FastAPI(title="Cardio Trace Simulator API", lifespan=lifespan)
app.include_router(router)


# TODO: This is a temporary handler for all exceptions. We should have more specific handlers for different types of exceptions.
@app.exception_handler(Exception)
async def runtime_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Convert uncaught Exceptions into a stable API response shape.
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )
