from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from .schemas import (
    DeviceInfo,
    DevicesResponse,
    HealthResponse,
    SimulationStatusResponse,
)


router = APIRouter()


def get_simulator(request: Request):
    return request.app.state.simulator


def get_config_path(request: Request):
    return request.app.state.config_path


@router.get("/health", response_model=HealthResponse)
async def health(simulator=Depends(get_simulator)) -> HealthResponse:
    state = simulator.state
    return HealthResponse(
        status="ok",
        simulator_state=state.value,
    )


@router.get("/simulation/status", response_model=SimulationStatusResponse)
async def simulation_status(
    simulator=Depends(get_simulator), config_path=Depends(get_config_path)
):
    state = simulator.state

    payload = {
        "state": state.value,
        "config_path": config_path,
    }

    if state.value == "ERROR":
        last_error = simulator.last_error
        payload["last_error"] = repr(last_error)
        return JSONResponse(status_code=503, content=payload)

    return SimulationStatusResponse(
        state=state.value,
        config_path=config_path,
    )


@router.post("/simulation/start")
async def simulation_start(simulator=Depends(get_simulator)):
    await simulator.start()
    state = simulator.state
    return {"state": state.value}


@router.post("/simulation/pause")
async def simulation_pause(simulator=Depends(get_simulator)):
    await simulator.pause()
    state = simulator.state
    return {"state": state.value}


@router.post("/simulation/stop")
async def simulation_stop(simulator=Depends(get_simulator)):
    """Full teardown: cancel device tasks and disconnect MQTT (also used on app shutdown)."""
    await simulator.stop()
    state = simulator.state
    return {"state": state.value}


@router.get("/devices", response_model=DevicesResponse)
async def list_devices(simulator=Depends(get_simulator)) -> DevicesResponse:
    device_configs = simulator.devices_config
    devices = [DeviceInfo(**device) for device in device_configs]
    return DevicesResponse(devices=devices)
