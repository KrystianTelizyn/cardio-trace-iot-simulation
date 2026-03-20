from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any
from pathlib import Path
import json
from hr_monitor.exceptions import InvalidConfigurationError


@dataclass(frozen=True)
class HRDeviceConfig:
    """Configuration for a single simulated HR monitor device."""

    device_id: str
    record_tag: str
    payload_format: str
    topic: str
    hr_frame: int = 5
    hrv_frame: int = 30

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HRDeviceConfig:
        return cls(
            device_id=data["device_id"],
            record_tag=data["record_tag"],
            payload_format=data["payload_format"],
            topic=data["topic"],
            hr_frame=data.get("hr_frame", 5),
            hrv_frame=data.get("hrv_frame", 30),
        )


@dataclass(frozen=True)
class HRSimulatorConfig:
    """Configuration for the simulator."""

    devices: Iterable[HRDeviceConfig]
    qos: int = 0
    retain: bool = False

    @classmethod
    def from_json(cls, json_str: str) -> HRSimulatorConfig:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(
                f"Failed to parse simulation configuration: {json_str}"
            ) from e
        devices = [HRDeviceConfig.from_dict(d) for d in data["devices"]]
        return cls(
            devices=devices,
            qos=data.get("qos", 0),
            retain=data.get("retain", False),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> HRSimulatorConfig:
        try:
            text = Path(path).read_text()
        except FileNotFoundError as e:
            raise InvalidConfigurationError(
                f"Simulation configuration file not found: {path}"
            ) from e
        return cls.from_json(text)
