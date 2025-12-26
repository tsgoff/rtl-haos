import types

import sensors_system


def _fake_vmem(percent=12.3):
    return types.SimpleNamespace(percent=percent)


def test_system_monitor_read_stats_disk_failure_omits_sys_disk(mocker):
    """Covers disk_usage exception path (sys_disk key omitted)."""

    # Avoid the 1s cpu_percent interval in real psutil
    mocker.patch("sensors_system.psutil.cpu_percent", return_value=1.0)
    mocker.patch("sensors_system.psutil.virtual_memory", return_value=_fake_vmem(50.0))

    fake_proc = mocker.Mock()
    fake_proc.memory_info.return_value = types.SimpleNamespace(rss=10 * 1024 * 1024)
    mocker.patch("sensors_system.psutil.Process", return_value=fake_proc)
    mocker.patch("sensors_system.psutil.boot_time", return_value=0)

    mocker.patch("sensors_system.shutil.disk_usage", side_effect=OSError("no disk"))
    mocker.patch("sensors_system.psutil.sensors_temperatures", return_value={})

    mon = sensors_system.SystemMonitor()
    stats = mon.read_stats()

    assert "sys_disk" not in stats


def test_system_monitor_read_stats_temp_fallback_first_sensor(mocker):
    """Covers temperature fallback loop (first available sensor).

    This hits the for-loop branch when neither 'cpu_thermal' nor 'coretemp' exists.
    """

    mocker.patch("sensors_system.psutil.cpu_percent", return_value=1.0)
    mocker.patch("sensors_system.psutil.virtual_memory", return_value=_fake_vmem(50.0))

    fake_proc = mocker.Mock()
    fake_proc.memory_info.return_value = types.SimpleNamespace(rss=10 * 1024 * 1024)
    mocker.patch("sensors_system.psutil.Process", return_value=fake_proc)
    mocker.patch("sensors_system.psutil.boot_time", return_value=0)

    mocker.patch("sensors_system.shutil.disk_usage", return_value=(100, 50, 50))

    class Entry:
        def __init__(self, current):
            self.current = current

    mocker.patch(
        "sensors_system.psutil.sensors_temperatures",
        return_value={"mystery": [Entry(42.0)]},
    )

    mon = sensors_system.SystemMonitor()
    stats = mon.read_stats()

    assert stats["sys_temp"] == 42.0
