import importlib
import importlib.util
import pathlib
import runpy

import pytest

import system_monitor


def test_system_stats_loop_bridge_stats_error_is_caught(mocker, capsys):
    """Covers [ERROR] Bridge Stats update failed path."""

    mqtt = mocker.Mock()
    mqtt.tracked_devices = {"dev1"}
    mqtt.send_sensor = mocker.Mock(side_effect=RuntimeError("boom"))

    mocker.patch.object(system_monitor, "PSUTIL_AVAILABLE", False)
    mocker.patch("system_monitor.time.sleep", side_effect=InterruptedError("stop"))

    with pytest.raises(InterruptedError):
        system_monitor.system_stats_loop(mqtt, "ID", "MODEL")

    out = capsys.readouterr().out
    assert "Bridge Stats update failed" in out


def test_system_stats_loop_hardware_stats_error_is_caught(mocker, capsys):
    """Covers [SYSTEM ERROR] Hardware stats failed path."""

    class DummyMon:
        def read_stats(self):
            raise RuntimeError("broken")

    mqtt = mocker.Mock()
    mqtt.tracked_devices = set()
    mqtt.send_sensor = mocker.Mock()

    mocker.patch.object(system_monitor, "PSUTIL_AVAILABLE", True)
    mocker.patch.object(system_monitor, "SystemMonitor", return_value=DummyMon())
    mocker.patch("system_monitor.time.sleep", side_effect=InterruptedError("stop"))

    with pytest.raises(InterruptedError):
        system_monitor.system_stats_loop(mqtt, "ID", "MODEL")

    out = capsys.readouterr().out
    assert "Hardware stats failed" in out


def test_system_monitor_import_guard_handles_find_spec_valueerror(monkeypatch, capsys):
    """Covers importlib.util.find_spec ValueError handling in module import."""

    def boom(_name: str):
        raise ValueError("bad spec")

    monkeypatch.setattr(importlib.util, "find_spec", boom)

    path = pathlib.Path(__file__).resolve().parents[1] / "system_monitor.py"
    ns = runpy.run_path(str(path))

    assert ns["PSUTIL_AVAILABLE"] is False
    assert "psutil" in capsys.readouterr().out.lower()
