from typing import List, Dict, Tuple
from datetime import timedelta, datetime
from itertools import cycle, islice
from asyncio import sleep
import pyhrv.time_domain as td
from .formats import PayloadResolver


class HRMonitorDevice:
    def __init__(
        self,
        device_id: str,
        rr_list: List[int],
        payload_format: str,
        hr_frame: int = 5,
        hrv_frame: int = 30,
        start_time: datetime = None,
    ):
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
            return self.hrv_collection[: self.hrv_frame - 1]
        else:
            return None

    def calculate_hrv_stats(self, intervals: List[int]) -> Tuple[int, float, float]:
        hr = int(td.hr_parameters(nni=intervals)["hr_mean"])
        sdnn, rmssd = None, None
        if self.hrv_window_ready:
            sdnn = round(td.sdnn(nni=self.hrv_window())["sdnn"], 2)
            rmssd = round(td.rmssd(nni=self.hrv_window())["rmssd"], 2)
        return hr, sdnn, rmssd

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
