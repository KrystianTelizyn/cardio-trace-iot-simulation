from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from hr_monitor import HRSimulatorConfig, HRMonitorMqttSimulator
from hr_monitor.adapters import AioMqttClientAdapter
from hr_monitor.exceptions import HRMonitorException
from rr_repository import RecordRepository
from rr_repository.exceptions import RRRepositoryException
from .error_handlers import register_exception_handlers
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


register_exception_handlers(app)
