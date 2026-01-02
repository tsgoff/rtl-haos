import os
import pytest

pytestmark = pytest.mark.integration


def _find_flag_value(cmd, flag):
    try:
        i = cmd.index(flag)
    except ValueError:
        return None
    if i + 1 >= len(cmd):
        return None
    return cmd[i + 1]


def _skip_if_disabled():
    if os.getenv("RUN_RTL433_TESTS", "0") != "1":
        pytest.skip("RUN_RTL433_TESTS not enabled")


def test_rtl_loop_builds_cmd_includes_device_freq_rate(monkeypatch):
    """
    rtl_loop is designed to run forever. This test stops it immediately by raising
    KeyboardInterrupt from the patched subprocess.Popen (KeyboardInterrupt is a BaseException
    and typically won't be swallowed by broad 'except Exception' handlers).
    """
    _skip_if_disabled()

    import rtl_manager  # your module
    captured = {"cmd": None}

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        raise KeyboardInterrupt()

    monkeypatch.setattr(rtl_manager.subprocess, "Popen", fake_popen)

    radio = {
        "index": 0,
        "freq": "433.92M",
        "rate": "250k",
        "hop_interval": 0,
        "name": "TestRadio1",
        "id": "101",
        "slot": 0,
    }

    with pytest.raises(KeyboardInterrupt):
        rtl_manager.rtl_loop(radio, object(), object(), "sysid", "sysmodel")

    cmd = captured["cmd"]
    assert cmd is not None, "rtl_loop did not reach subprocess.Popen"
    cmd_str = " ".join(map(str, cmd))

    assert "rtl_433" in cmd_str, f"Expected rtl_433 in command, got: {cmd}"
    assert ("-d" in cmd and str(radio["index"]) in cmd) or ("-d0" in cmd_str), f"Expected device index in cmd: {cmd}"
    assert "433.92M" in cmd_str, f"Expected frequency in cmd: {cmd}"
    assert ("-s" in cmd and "250k" in cmd) or ("250k" in cmd_str), f"Expected rate in cmd: {cmd}"


def test_rtl_loop_multi_freq_adds_hop_interval_when_needed(monkeypatch):
    _skip_if_disabled()

    import rtl_manager
    captured = {"cmd": None}

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        raise KeyboardInterrupt()

    monkeypatch.setattr(rtl_manager.subprocess, "Popen", fake_popen)

    radio = {
        "index": 1,
        "freq": "868M,915M",
        "rate": "1024k",
        "hop_interval": 15,
        "name": "TestRadio2",
        "id": "102",
        "slot": 1,
    }

    with pytest.raises(KeyboardInterrupt):
        rtl_manager.rtl_loop(radio, object(), object(), "sysid", "sysmodel")

    cmd = captured["cmd"]
    assert cmd is not None, "rtl_loop did not reach subprocess.Popen"
    cmd_str = " ".join(map(str, cmd))

    assert "868M" in cmd_str and "915M" in cmd_str, f"Expected both freqs in cmd: {cmd}"

    hop_val = _find_flag_value(cmd, "-H")
    if hop_val is None:
        assert ("-H15" in cmd_str) or ("hop" in cmd_str.lower() and "15" in cmd_str), f"Expected hop interval evidence in cmd: {cmd}"
    else:
        assert str(hop_val).strip() == "15", f"Expected hop interval 15, got {hop_val} in cmd: {cmd}"


def test_rtl_loop_single_freq_does_not_require_hop(monkeypatch):
    _skip_if_disabled()

    import rtl_manager
    captured = {"cmd": None}

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        raise KeyboardInterrupt()

    monkeypatch.setattr(rtl_manager.subprocess, "Popen", fake_popen)

    radio = {
        "index": 2,
        "freq": "915M",
        "rate": "1024k",
        "hop_interval": 15,
        "name": "TestRadio3",
        "id": "103",
        "slot": 2,
    }

    with pytest.raises(KeyboardInterrupt):
        rtl_manager.rtl_loop(radio, object(), object(), "sysid", "sysmodel")

    cmd = captured["cmd"]
    assert cmd is not None
    cmd_str = " ".join(map(str, cmd))
    assert "915M" in cmd_str


def test_build_cmd_includes_global_and_per_radio_passthrough(monkeypatch):
    """Passthrough: global RTL_433_ARGS + per-radio args both appear in command."""
    _skip_if_disabled()

    import config
    import rtl_manager

    monkeypatch.setattr(config, "RTL_433_ARGS", '-p 0 -t "direct_samp=1"', raising=False)

    radio = {
        "index": 0,
        "freq": "433.92M",
        "rate": "250k",
        "hop_interval": 0,
        "name": "TestRadioPT",
        "id": "201",
        "slot": 0,
        "args": "-g 0 -T 2",
    }

    cmd = rtl_manager.build_rtl_433_command(radio)
    cmd_str = " ".join(map(str, cmd))

    # Global passthrough args
    assert "-p" in cmd and "0" in cmd, f"Expected global -p 0 in cmd: {cmd}"
    assert "-t" in cmd and "direct_samp=1" in cmd, f"Expected global -t direct_samp=1 in cmd: {cmd}"

    # Per-radio passthrough args
    assert "-g" in cmd and "0" in cmd, f"Expected per-radio -g 0 in cmd: {cmd}"
    assert "-T" in cmd and "2" in cmd, f"Expected per-radio -T 2 in cmd: {cmd}"

    # RTL-HAOS forces JSON output for parsing
    assert cmd_str.endswith("-F json -M level"), f"Expected forced JSON output at end, got: {cmd_str}"


def test_build_cmd_accepts_json_list_global_args(monkeypatch):
    """Passthrough: global args may be provided as a JSON list string."""
    _skip_if_disabled()

    import config
    import rtl_manager

    monkeypatch.setattr(config, "RTL_433_ARGS", '["-p", "1", "-g", "0"]', raising=False)

    radio = {
        "index": 1,
        "freq": "433.92M",
        "rate": "250k",
        "hop_interval": 0,
        "name": "TestRadioJSON",
        "id": "202",
        "slot": 1,
    }

    cmd = rtl_manager.build_rtl_433_command(radio)
    assert "-p" in cmd and "1" in cmd
    assert "-g" in cmd and "0" in cmd


def test_build_cmd_config_path_resolves_relative(monkeypatch, tmp_path):
    """Passthrough: RTL_433_CONFIG_PATH should resolve relative paths (cwd)."""
    _skip_if_disabled()

    import config
    import rtl_manager

    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "rtl_433.conf"
    cfg.write_text("# test\n-g 0\n", encoding="utf-8")

    monkeypatch.setattr(config, "RTL_433_CONFIG_PATH", "rtl_433.conf", raising=False)
    monkeypatch.setattr(config, "RTL_433_CONFIG_INLINE", "", raising=False)

    radio = {
        "index": 2,
        "freq": "433.92M",
        "rate": "250k",
        "hop_interval": 0,
        "name": "TestRadioCfgPath",
        "id": "203",
        "slot": 2,
    }

    cmd = rtl_manager.build_rtl_433_command(radio)
    assert "-c" in cmd, f"Expected -c <path> in cmd: {cmd}"
    c_idx = cmd.index("-c")
    assert cmd[c_idx + 1] == str(cfg), f"Expected resolved config path {cfg}, got {cmd[c_idx + 1]}"


def test_build_cmd_inline_config_writes_temp_file(monkeypatch):
    """Passthrough: inline config should be written and referenced via -c."""
    _skip_if_disabled()

    import config
    import rtl_manager

    monkeypatch.setattr(config, "RTL_433_CONFIG_PATH", "", raising=False)
    monkeypatch.setattr(config, "RTL_433_CONFIG_INLINE", "-g 0\n-R 11\n", raising=False)

    radio = {
        "index": 3,
        "freq": "433.92M",
        "rate": "250k",
        "hop_interval": 0,
        "name": "TestRadioInline",
        "id": "204",
        "slot": 3,
    }

    cmd = rtl_manager.build_rtl_433_command(radio)
    assert "-c" in cmd, f"Expected -c <path> in cmd: {cmd}"
    c_idx = cmd.index("-c")
    cfg_path = cmd[c_idx + 1]
    assert cfg_path.startswith("/tmp/rtl_433_"), f"Expected temp config under /tmp, got {cfg_path}"

    # File should exist and contain our content.
    with open(cfg_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "-g 0" in content and "-R 11" in content
