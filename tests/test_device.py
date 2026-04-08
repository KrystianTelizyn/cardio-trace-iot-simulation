import pytest
from hr_monitor.device import HRMonitorDevice
from hr_monitor.exceptions import DeviceInitializationError, HRVCalculationError
from hr_monitor.formats import PayloadResolver, PayloadTemplates
from datetime import datetime, timedelta


def test_token_replacements_in_frame():
    simple_payload = "<hr> <sdnn> <rmssd> <time> <frame> <device_id>"
    device = HRMonitorDevice(
        device_id="Device_A", rr_list=[1000, 1000, 1000], payload_format=simple_payload
    )

    token_replacements = {
        "<hr>": 10,
        "<sdnn>": 11,
        "<rmssd>": 12,
        "<time>": "2021-01-01T00:00:00Z",
        "<frame>": 1,
        "<device_id>": "Device_A",
    }
    frame = device.build_frame(token_replacements)
    assert frame == "10 11 12 2021-01-01T00:00:00Z 1 Device_A"


@pytest.mark.asyncio
async def test_hrv_window_ready():
    rr_example = [10 for _ in range(30)]
    simple_payload = "<hr>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    for _ in range(5):
        assert device.hrv_window_ready is False
        await device.obtain_next_measurement_frame()
    for _ in range(5):
        assert device.hrv_window_ready is True
        await device.obtain_next_measurement_frame()


@pytest.mark.asyncio
async def test_hrv_none_when_hrv_window_not_ready():
    rr_example = [10 for _ in range(30)]
    simple_payload = "<sdnn> <rmssd>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "None None"


@pytest.mark.asyncio
async def test_frame_increment():
    rr_example = [10 for _ in range(30)]
    simple_payload = "<frame>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "1"
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "2"
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "3"
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "4"


@pytest.mark.asyncio
async def test_device_id_in_frame():
    rr_example = [10 for _ in range(30)]
    simple_payload = "<device_id>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "Device_A"


@pytest.mark.asyncio
async def test_time_in_frame():
    # 1000 ms equivalent inone HR window(frame)
    rr_example = [500 for _ in range(10)]
    simple_payload = "<time>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    frame_a = await device.obtain_next_measurement_frame()
    frame_b = await device.obtain_next_measurement_frame()
    # parse iso string time to datetime
    time_a = datetime.fromisoformat(frame_a)
    time_b = datetime.fromisoformat(frame_b)
    # assert time_b is at least 1 second after time_a
    assert time_b - time_a >= timedelta(milliseconds=1000)
    assert time_b - time_a <= timedelta(milliseconds=1100)


@pytest.mark.asyncio
async def test_iso_time_format_in_frame():
    rr_example = [10 for _ in range(30)]
    simple_payload = "<time>"
    current_time = datetime.now()
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    frame = await device.obtain_next_measurement_frame()
    # parse iso string time to datetime
    # assert no error is raised
    try:
        time = datetime.fromisoformat(frame)
    except ValueError:
        assert False
    # assert time is within 1 second of current time
    assert time - current_time >= timedelta(milliseconds=20)
    assert time - current_time <= timedelta(milliseconds=120)


def test_cycling_rr_list():
    rr_example = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    cycle_size = 4
    simple_payload = "<hr>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=cycle_size,
        hrv_frame=9,
    )
    assert device._sample_rr(cycle_size) == [0, 1, 2, 3]
    assert device._sample_rr(cycle_size) == [4, 5, 6, 7]
    assert device._sample_rr(cycle_size) == [8, 9, 0, 1]
    assert device._sample_rr(cycle_size) == [2, 3, 4, 5]
    assert device._sample_rr(cycle_size) == [6, 7, 8, 9]
    assert device._sample_rr(cycle_size) == [0, 1, 2, 3]
    assert device._sample_rr(cycle_size) == [4, 5, 6, 7]
    assert device._sample_rr(cycle_size) == [8, 9, 0, 1]
    assert device._sample_rr(cycle_size) == [2, 3, 4, 5]
    assert device._sample_rr(cycle_size) == [6, 7, 8, 9]


@pytest.mark.asyncio
async def test_using_hr_window_for_hr_calculation(mocker):
    rr_example = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    simple_payload = "<hr>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    # mock and assert that calculate_hr is called with the correct arguments
    mock_calculate_hr = mocker.patch.object(device, "calculate_hr")
    mock_calculate_hr.return_value = 0
    await device.obtain_next_measurement_frame()
    mock_calculate_hr.assert_called_with([1, 2])
    await device.obtain_next_measurement_frame()
    mock_calculate_hr.assert_called_with([3, 4])


@pytest.mark.asyncio
async def test_using_hrv_window_for_hrv_calculation(mocker):
    rr_example = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    simple_payload = "<sdnn> <rmssd>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=5,
    )
    # mock and assert that calculate_hrv called with the hrv window
    mock_calculate_hrv = mocker.patch.object(device, "calculate_hrv")
    mock_calculate_hrv.return_value = (0, 0)
    await device.obtain_next_measurement_frame()
    mock_calculate_hrv.assert_not_called()
    await device.obtain_next_measurement_frame()
    mock_calculate_hrv.assert_not_called()
    await device.obtain_next_measurement_frame()
    mock_calculate_hrv.assert_called_with([2, 3, 4, 5, 6])
    await device.obtain_next_measurement_frame()
    mock_calculate_hrv.assert_called_with([4, 5, 6, 7, 8])
    await device.obtain_next_measurement_frame()
    mock_calculate_hrv.assert_called_with([6, 7, 8, 9, 10])


@pytest.mark.asyncio
async def test_calculate_hrv_stats(mocker):
    rr_example = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    simple_payload = "<hr> <sdnn> <rmssd>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=5,
    )
    # mock and assert that calculate_hrv_stats is called with the correct arguments
    mock_calculate_hrv_stats = mocker.patch.object(device, "calculate_hrv_stats")
    mock_calculate_hrv_stats.return_value = (100, 2.2, 3.3)
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "100 2.2 3.3"


@pytest.mark.asyncio
async def test_expected_hr_calculation():
    rr_example = [1000 for _ in range(10)]  # 1000 ms equivalent to 60 bpm
    simple_payload = "<hr>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
        hr_frame=2,
        hrv_frame=9,
    )
    result_frame = await device.obtain_next_measurement_frame()
    assert result_frame == "60"


def test_using_payload_resolve(mocker):
    # mock PayloadResolver.resolve to return a simple payload
    mocker.patch.object(PayloadResolver, "resolve", return_value="<hr> <sdnn> <rmssd>")
    device = HRMonitorDevice(
        device_id="Device_A", rr_list=[10, 10], payload_format=PayloadTemplates.Apple
    )
    assert device.payload_format == "<hr> <sdnn> <rmssd>"


@pytest.mark.asyncio
async def test_common_usage_of_device():
    rr_example = [250 for _ in range(200)]  # 250 ms equivalent to 240 bpm
    device = HRMonitorDevice(
        device_id="runner", rr_list=rr_example, payload_format=PayloadTemplates.Apple
    )
    result_frame = ""
    for _ in range(10):
        result_frame = await device.obtain_next_measurement_frame()
    assert '"value_bpm": 240' in result_frame
    assert '"timestamp_iso": ' in result_frame
    assert '"sequence_number": 10' in result_frame
    assert '"deviceId": "runner"' in result_frame


def test_empty_device_id_raises_device_initialization_error():
    with pytest.raises(DeviceInitializationError) as e:
        HRMonitorDevice(
            device_id="", rr_list=[10, 10], payload_format=PayloadTemplates.Apple
        )
    assert "Device ID is required" in str(e.value)


def test_empty_rr_list_raises_device_initialization_error():
    with pytest.raises(DeviceInitializationError) as e:
        HRMonitorDevice(
            device_id="Device_A", rr_list=[], payload_format=PayloadTemplates.Apple
        )
    assert "RR list is required" in str(e.value)


def test_empty_payload_format_raises_device_initialization_error():
    with pytest.raises(DeviceInitializationError) as e:
        HRMonitorDevice(device_id="Device_A", rr_list=[10, 10], payload_format="")
    assert "Payload format is required" in str(e.value)


@pytest.mark.asyncio
async def test_hrv_calculation_error(mocker):
    rr_example = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # Correct way to patch inside @src/hr_monitor/device.py
    mock_hr_mean_bpm = mocker.patch("hr_monitor.device.hr_mean_bpm")
    mock_hr_mean_bpm.side_effect = HRVCalculationError("Test error")

    simple_payload = "<sdnn> <rmssd>"
    device = HRMonitorDevice(
        device_id="Device_A",
        rr_list=rr_example,
        payload_format=simple_payload,
    )
    with pytest.raises(HRVCalculationError):
        # Since obtain_next_measurement_frame is async, we need to run it in an event loop
        await device.obtain_next_measurement_frame()
