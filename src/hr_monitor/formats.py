from enum import Enum
from pathlib import Path

_PAYLOADS_DIR = Path(__file__).parent / "payloads"


class PayloadTemplates(str, Enum):
    """Payload format templates loaded from hr_monitor/payloads/.
    Use with HRMonitorDevice(payload_format=Payloads.Apple) etc.
    """

    Apple = "PayloadTemplates.Apple"
    EHR = "PayloadTemplates.EHR"
    Garmin = "PayloadTemplates.Garmin"


_cached_payloads = {
    PayloadTemplates.Apple: (_PAYLOADS_DIR / "apple.json").read_text(),
    PayloadTemplates.EHR: (_PAYLOADS_DIR / "ehr.json").read_text(),
    PayloadTemplates.Garmin: (_PAYLOADS_DIR / "garmin.json").read_text(),
}


class PayloadResolver:
    @classmethod
    def resolve(cls, payload_candidate: str | PayloadTemplates) -> str:
        if isinstance(payload_candidate, PayloadTemplates) or (
            payload_candidate in PayloadTemplates
        ):
            return _cached_payloads[payload_candidate]
        if not isinstance(payload_candidate, str):
            raise ValueError(f"Unsupported payload format: {type(payload_candidate)}")
        return payload_candidate
