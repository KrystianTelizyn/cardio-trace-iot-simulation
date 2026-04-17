import pytest

from hr_monitor.exceptions import HRVCalculationError
from hr_monitor.metrics import hr_mean_bpm, sdnn_ms, rmssd_ms


def test_hr_mean_bpm_expected_value():
    assert hr_mean_bpm([1000, 500]) == 90.0


def test_sdnn_ms_expected_value():
    assert sdnn_ms([1000, 1100, 900]) == 100.0


def test_rmssd_ms_expected_value():
    assert rmssd_ms([1000, 1100, 900]) == pytest.approx(158.11, abs=0.01)


@pytest.mark.parametrize(
    "fn,values,expected_message",
    [
        (hr_mean_bpm, [], "RR intervals list cannot be empty."),
        (sdnn_ms, [1000], "SDNN requires at least two RR intervals."),
        (rmssd_ms, [1000], "RMSSD requires at least two RR intervals."),
    ],
)
def test_metric_validations(fn, values, expected_message):
    with pytest.raises(HRVCalculationError, match=expected_message):
        fn(values)
