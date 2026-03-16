from enum import Enum
from pathlib import Path

_PAYLOADS_DIR = Path(__file__).parent / "payloads"


class PayloadTemplates(str, Enum):
    """Payload format templates loaded from hr_monitor/payloads/.
    Use with HRMonitorDevice(payload_format=Payloads.Apple) etc.
    """

    Apple = (_PAYLOADS_DIR / "apple.json").read_text()
    EHR = (_PAYLOADS_DIR / "ehr.json").read_text()
    Garmin = (_PAYLOADS_DIR / "garmin.json").read_text()
