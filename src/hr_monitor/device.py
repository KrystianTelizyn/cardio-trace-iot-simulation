from typing import List, Dict, Tuple
from datetime import timedelta, datetime
from itertools import cycle, islice
from asyncio import sleep

from .formats import PayloadResolver
from .exceptions import DeviceInitializationError
from .metrics import hr_mean_bpm, sdnn_ms, rmssd_ms


class HRMonitorDevice:
    """
    Emulates a heart rate monitoring device capable of generating RR intervals,
    assembling HR and HRV measurement frames, and formatting telemetry payloads.

    Args:
        device_id (str): Unique identifier for the device.
        rr_list (List[int]): Sequence of RR intervals (ms) to cycle through.
        payload_format (str): Template or format string for telemetry output.
        hr_frame (int, optional): Number of RR samples per HR calculation. Defaults to 5.
        hrv_frame (int, optional): Number of RR samples in sliding window for HRV stats. Defaults to 30.
        start_time (datetime, optional): Time to set as first sample.

    Raises:
        DeviceInitializationError: If required parameters are missing or invalid.

    Methods:
        _sample_rr(samples): Collects the next N RR intervals from source.
        _update_hrv_window(intervals): Appends RR intervals to sliding window, trimming to `hrv_frame`.
        hrv_window(): Returns the current HRV window if sufficient samples, else None.
        calculate_hrv(intervals): Calculates SDNN and RMSSD from intervals.
        calculate_hrv_stats(intervals): Calculates HR, SDNN, and RMSSD, handling error cases.
        obtain_next_measurement_frame(): Async method to gather next frame as per payload format.
    """

    def __init__(
        self,
        device_id: str,
        rr_list: List[int],
        payload_format: str,
        hr_frame: int = 5,
        hrv_frame: int = 30,
        start_time: datetime = None,
    ):
        if device_id is None or device_id == "":
            raise DeviceInitializationError("Device ID is required")
        if payload_format is None or payload_format == "":
            raise DeviceInitializationError("Payload format is required")
        if not rr_list or len(rr_list) == 0:
            raise DeviceInitializationError("RR list is required")

        self.device_id = device_id
        self.rr_source = cycle(rr_list)
        self.payload_format = PayloadResolver.resolve(payload_format)
        self.hr_frame = hr_frame
        self.hrv_frame = hrv_frame
        self.hrv_collection: List[int] = []
        self.last_sample_time = datetime.now()
        if start_time:
            self.last_sample_time = start_time
        self.frame_number = 0

    def _sample_rr(self, samples=5) -> List[int]:
        return list(islice(self.rr_source, samples))

    def _update_hrv_window(self, intervals: List[int]):
        self.hrv_collection.extend(intervals)
        self.hrv_collection = self.hrv_collection[-self.hrv_frame :]

    def hrv_window(self) -> List[int] | None:
        if self.hrv_window_ready:
            return self.hrv_collection[0 : self.hrv_frame]
        else:
            return None

    def calculate_hrv(self, intervals: List[int]) -> Tuple[float, float]:
        sdnn = round(sdnn_ms(intervals), 2)
        rmssd = round(rmssd_ms(intervals), 2)
        return sdnn, rmssd

    def calculate_hrv_stats(self, intervals: List[int]) -> Tuple[float, float]:
        hr, sdnn, rmssd = None, None, None
        hr = self.calculate_hr(intervals)
        if self.hrv_window_ready:
            sdnn, rmssd = self.calculate_hrv(self.hrv_window())
        return hr, sdnn, rmssd

    def calculate_hr(self, intervals: List[int]) -> int:
        hr = int(hr_mean_bpm(intervals))
        return hr

    @property
    def hrv_window_ready(self) -> bool:
        return len(self.hrv_collection) >= self.hrv_frame

    async def obtain_next_measurement_frame(self) -> str:
        rr_intervals = self._sample_rr(self.hr_frame)
        self._update_hrv_window(rr_intervals)
        self.frame_number += 1
        self.last_sample_time += timedelta(milliseconds=sum(rr_intervals))

        hr, sdnn, rmssd = self.calculate_hrv_stats(rr_intervals)

        token_replacements = {
            "<hr>": hr,
            "<sdnn>": sdnn,
            "<rmssd>": rmssd,
            "<time>": self.last_sample_time.isoformat(),
            "<frame>": self.frame_number,
            "<device_id>": self.device_id,
        }

        await sleep(sum(rr_intervals) / 1000)

        return self.build_frame(token_replacements)

    def build_frame(self, token_replacements: Dict[str, str]) -> str:
        json_frame = self.payload_format

        for token, replacement in token_replacements.items():
            json_frame = json_frame.replace(token, str(replacement))

        return json_frame
