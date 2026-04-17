Cardio Trace IoT Simulation
===========================

**This is a part of [Cardio Trace Platform](https://github.com/KrystianTelizyn/cardio-trace-platform)**
Cardio Trace IoT Simulation is a Python toolkit for simulating heart‑rate monitor devices that publish data over MQTT using real RR‑interval recordings.

What it does
------------

- Imports RR data from the PhysioNet “RR interval time series from healthy subjects” dataset into a local SQLite database.
- Provides a repository API (`RecordRepository`) to list records and load RR‑interval series.
- Simulates HR devices (`HRMonitorMqttSimulator`) that replay RR‑interval data and publish frames via a user‑provided MQTT client.

Requirements
------------

- Python 3.13+

Install dependencies with:

```bash
pip install -e .
# or, if you use uv:
uv sync
```

Basic usage
-----------

1. Download and import PhysioNet data:

```bash
make download-physionet
make import-physionet
```

2. Use the RR repository:

```python
from rr_repository import RecordRepository

repo = RecordRepository()
records = repo.list_records()
rr = repo.get_record_data("physionet-rr-000")
```

3. Run a simple simulator (sketch):

```python
from hr_monitor import HRDeviceConfig, HRSimulatorConfig, HRMonitorMqttSimulator
from hr_monitor.adapters import AioMqttClientAdapter
from hr_monitor.formats import PayloadTemplates
from rr_repository import RecordRepository
import asyncio

repo = RecordRepository()
devices = [
    HRDeviceConfig(
        device_id="dev-1",
        record_tag="physionet-rr-000",
        payload_format=PayloadTemplates.Apple,
        topic="/bus/dev-1"
    )
]
cfg = HRSimulatorConfig(devices=devices)
mqtt_client = AioMqttClientAdapter(hostname="localhost", port=1883)
sim = HRMonitorMqttSimulator(repo, cfg, mqtt_client)
asyncio.run(sim.start())
```


Running the REST API
--------------------

You can run a small FastAPI service that wraps `HRMonitorMqttSimulator` and exposes HTTP endpoints to start/stop the simulation and inspect devices.

1. Set required environment variables:

```bash
export SIM_CONFIG_PATH=tests/rr_config.json  # or your own config JSON
export MQTT_HOST=localhost
export MQTT_PORT=1883
export RR_DB_PATH=data/rr_records.db
```

2. Run the API with uvicorn (single worker to keep one simulator instance per process):

```bash
uvicorn rest.app:app --host 0.0.0.0 --port 8000 --workers 1
```

Alternatively, run the module directly:

```bash
python -m rest
```

For local development, you can also run the stack with Docker Compose:

```bash
make compose-up
```

3. Example requests:

```bash
# Health check
curl http://localhost:8000/health

# Start/stop the simulation
curl -X POST http://localhost:8000/simulation/start
curl -X POST http://localhost:8000/simulation/stop

# Get simulator status
curl http://localhost:8000/simulation/status

# List devices and their MQTT topics
curl http://localhost:8000/devices
```

License
-------

This project is licensed under the MIT License. See the `LICENSE` file for details.
