import pytest
from hr_monitor.formats import PayloadTemplates


@pytest.fixture
def simulated_cached_payloads(monkeypatch):
    fake_cache = {
        PayloadTemplates.Apple: "foo",
        PayloadTemplates.EHR: "bar",
        PayloadTemplates.Garmin: "baz",
    }
    monkeypatch.setattr("hr_monitor.formats._cached_payloads", fake_cache)
    return fake_cache
