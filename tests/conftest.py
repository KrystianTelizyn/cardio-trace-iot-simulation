import pytest
import json
from hr_monitor.formats import PayloadTemplates
from hr_monitor.simulator import HRDeviceConfig


@pytest.fixture
def simulated_cached_payloads(monkeypatch):
    fake_cache = {
        PayloadTemplates.Apple: "foo",
        PayloadTemplates.EHR: "bar",
        PayloadTemplates.Garmin: "baz",
    }
    monkeypatch.setattr("hr_monitor.formats._cached_payloads", fake_cache)
    return fake_cache


@pytest.fixture
def example_config():
    config_dict = {
        "devices": [
            {
                "device_id": "runner",
                "payload_format": "<device_id> <frame>",
                "topic": "example/runner",
                "hr_frame": 2,
                "hrv_frame": 9,
                "record_tag": "patient-xyz",
            },
            {
                "device_id": "walker",
                "payload_format": "<device_id> <frame>",
                "topic": "example/walker",
                "hr_frame": 2,
                "hrv_frame": 9,
                "record_tag": "patient-abc",
            },
        ],
        "qos": 0,
        "retain": False,
    }
    return json.dumps(config_dict)


@pytest.fixture
def expected_devices_list():
    return [
        HRDeviceConfig(
            device_id="runner",
            payload_format="PayloadTemplates.Apple",
            topic="example/runner",
            hr_frame=2,
            hrv_frame=9,
            record_tag="patient-xyz",
        ),
        HRDeviceConfig(
            device_id="walker",
            payload_format="PayloadTemplates.Garmin",
            topic="example/walker",
            hr_frame=2,
            hrv_frame=9,
            record_tag="patient-abc",
        ),
    ]


@pytest.fixture
def example_config_file():
    return "tests/example_config.json"
