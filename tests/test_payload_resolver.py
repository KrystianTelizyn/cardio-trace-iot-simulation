import pytest
from hr_monitor.formats import PayloadResolver
from hr_monitor.formats import PayloadTemplates
from hr_monitor.formats import _PAYLOADS_DIR
from hr_monitor.exceptions import InvalidPayloadTypeError


def test_resolves_payload_from_payload_templates_enum(simulated_cached_payloads):
    assert PayloadResolver.resolve(PayloadTemplates.Apple) == "foo"
    assert PayloadResolver.resolve(PayloadTemplates.EHR) == "bar"
    assert PayloadResolver.resolve(PayloadTemplates.Garmin) == "baz"


def test_resolves_payload_from_string(simulated_cached_payloads):
    assert PayloadResolver.resolve("foo") == "foo"
    assert PayloadResolver.resolve("bar") == "bar"
    assert PayloadResolver.resolve("baz") == "baz"


def test_resolves_payload_from_string_real_cached_payloads():
    assert PayloadResolver.resolve("foo") == "foo"
    assert PayloadResolver.resolve("bar") == "bar"
    assert PayloadResolver.resolve("baz") == "baz"


def test_raises_value_error_for_unknown_payload_type(simulated_cached_payloads):
    with pytest.raises(InvalidPayloadTypeError):
        PayloadResolver.resolve(123)


def test_cached_payloads_loaded_from_json_file():
    apple_payload = (_PAYLOADS_DIR / "apple.json").read_text()
    assert PayloadResolver.resolve(PayloadTemplates.Apple) == apple_payload
    ehr_payload = (_PAYLOADS_DIR / "ehr.json").read_text()
    assert PayloadResolver.resolve(PayloadTemplates.EHR) == ehr_payload
    garmin_payload = (_PAYLOADS_DIR / "garmin.json").read_text()
    assert PayloadResolver.resolve(PayloadTemplates.Garmin) == garmin_payload
