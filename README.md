Cardio Trace IoT Simulation
===========================

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
from hr_monitor import RecordRepository

repo = RecordRepository()
records = repo.list_records()
rr = repo.get_record_data("physionet-rr-000")
```

3. Run a simple simulator (sketch):

```python
from hr_monitor import HRDeviceConfig, HRSimulatorConfig, HRMonitorMqttSimulator, RecordRepository
import asyncio


class MyMqttClient:
    async def connect(self): ...
    async def publish(self, topic, payload, qos=0, retain=False): ...
    async def disconnect(self): ...


repo = RecordRepository()
devices = [HRDeviceConfig(device_id="dev-1", record_tag="physionet-rr-000", payload_format="json")]
cfg = HRSimulatorConfig(devices=devices, topic_builder=lambda d: f"iot/hr/{d}")
sim = HRMonitorMqttSimulator(repo, cfg, MyMqttClient())
asyncio.run(sim.start())
```

License
-------

This project is licensed under the MIT License. See the `LICENSE` file for details.
