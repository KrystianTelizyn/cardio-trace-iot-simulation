from hr_monitor.simulator import HRSimulatorConfig


def test_from_json_to_device(example_config, expected_devices_list):
    result = HRSimulatorConfig.from_json(example_config)
    assert result.devices == expected_devices_list
    assert result.qos == 0
    assert result.retain is False


def test_from_json_file_to_device(example_config_file, expected_devices_list):
    result = HRSimulatorConfig.from_json_file(example_config_file)
    assert result.devices == expected_devices_list
    assert result.qos == 0
    assert result.retain is False
