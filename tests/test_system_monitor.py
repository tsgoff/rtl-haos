import pytest
from sensors_system import SystemMonitor

def test_system_monitor_read_stats(mocker):
    """Verifies that system stats are gathered correctly."""
    # 1. Mock psutil to return known values
    mocker.patch("psutil.cpu_percent", return_value=15.5)
    mocker.patch("psutil.virtual_memory").return_value.percent = 42.0
    mocker.patch("psutil.boot_time", return_value=1000000)
    
    # Mock disk usage (shutil)
    mocker.patch("shutil.disk_usage").return_value = (100, 50, 50) # Total, Used, Free

    # Mock Temperature (Complex dictionary structure)
    mock_temps = {
        "cpu_thermal": [mocker.Mock(current=55.0)],
        "coretemp": [mocker.Mock(current=60.0)]
    }
    mocker.patch("psutil.sensors_temperatures", return_value=mock_temps)

    # 2. Instantiate and Read
    monitor = SystemMonitor()
    stats = monitor.read_stats()

    # 3. Assertions
    assert stats["sys_cpu"] == 15.5
    assert stats["sys_mem"] == 42.0
    assert stats["sys_temp"] == 55.0  # Should pick first available (cpu_thermal)
    assert "sys_uptime" in stats