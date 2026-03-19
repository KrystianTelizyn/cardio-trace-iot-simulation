from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    simulator_state: str


class SimulationStatusResponse(BaseModel):
    state: str
    config_path: Optional[str] = None


class DeviceInfo(BaseModel):
    device_id: str
    record_tag: str
    payload_format: str
    topic: str
    hr_frame: int
    hrv_frame: int


class DevicesResponse(BaseModel):
    devices: List[DeviceInfo]
