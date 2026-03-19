from __future__ import annotations

from fastapi import APIRouter, Request, Depends
import os
from .schemas import (
    DeviceInfo,
    DevicesResponse,
    HealthResponse,
    SimulationStatusResponse,
)


router = APIRouter()


def get_simulator(request: Request):
    return request.app.state.simulator


@router.get("/health", response_model=HealthResponse)
async def health(simulator=Depends(get_simulator)) -> HealthResponse:
    state = simulator.state
    return HealthResponse(
        status="ok",
        simulator_state=state.value,
    )


@router.get("/simulation/status", response_model=SimulationStatusResponse)
async def simulation_status(simulator=Depends(get_simulator)):
    state = simulator.state
    return SimulationStatusResponse(
        state=state.value,
        config_path=os.getenv("SIM_CONFIG_PATH"),
    )


@router.post("/simulation/start")
async def simulation_start(simulator=Depends(get_simulator)):
    await simulator.start()
    state = simulator.state
    return {"state": state.value}


@router.post("/simulation/stop")
async def simulation_stop(simulator=Depends(get_simulator)):
    await simulator.stop()
    state = simulator.state
    return {"state": state.value}


@router.post("/simulation/close")
async def simulation_close(simulator=Depends(get_simulator)):
    await simulator.close()
    state = simulator.state
    return {"state": state.value}


@router.get("/devices", response_model=DevicesResponse)
async def list_devices(simulator=Depends(get_simulator)) -> DevicesResponse:
    device_configs = simulator.devices_config
    devices = [DeviceInfo(**device) for device in device_configs]
    return DevicesResponse(devices=devices)
