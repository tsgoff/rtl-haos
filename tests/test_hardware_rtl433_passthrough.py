"""Hardware-only smoke tests for rtl_433 passthrough support.

These tests are intentionally skipped unless RUN_HARDWARE_TESTS=1.

Goal: prove that the passthrough fields we expose (global RTL_433_ARGS and
per-radio `args`) are actually passed to the real rtl_433 binary and rtl_433
can start and exit cleanly.

We do NOT assert any RF decodes (noisy / environment-dependent). We only assert
the process returns 0 and commonly-seen hardware issues are treated as skips.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

import config
from rtl_manager import build_rtl_433_command, discover_rtl_devices


def _require_env(name: str) -> None:
    if os.getenv(name) != "1":
        pytest.skip(f"Set {name}=1 to enable this test")


def _require_rtl433() -> str:
    exe = shutil.which("rtl_433")
    if not exe:
        pytest.skip("rtl_433 is not installed or not in PATH")
    return exe


def _skip_for_common_hw_errors(proc: subprocess.CompletedProcess[str]) -> None:
    combined = (proc.stdout + "\n" + proc.stderr).lower()
    if "no supported devices found" in combined:
        pytest.skip("No RTL-SDR device detected (rtl_433 reported none found)")
    if "usb_open error" in combined or "permission denied" in combined:
        pytest.skip("RTL-SDR present but not accessible (permissions/USB open error)")
    if "resource busy" in combined or "device or resource busy" in combined:
        pytest.skip("RTL-SDR device busy (another rtl_433/add-on instance likely running)")


@pytest.mark.hardware
def test_rtl433_passthrough_args_open_and_exit_cleanly(monkeypatch):
    """Run rtl_433 using build_rtl_433_command and verify passthrough flags apply.

    - Uses the first discovered RTL-SDR.
    - Adds a global passthrough flag (-p 0) and per-radio args (-g 0 -T 2).
    - -T 2 ensures rtl_433 exits quickly.
    """

    _require_env("RUN_HARDWARE_TESTS")
    exe = _require_rtl433()

    devices = discover_rtl_devices()
    if not devices:
        pytest.skip("No RTL-SDR devices discovered")

    # Match the multi-radio hardware smoke test style: exercise up to 3 dongles if present.
    indices = [d.get("index") for d in devices[:3]]
    indices = [i for i in indices if isinstance(i, int)]
    if not indices:
        pytest.skip("Discovered RTL-SDR indices missing/invalid")

    # Force the executable path so we test the real binary we located.
    monkeypatch.setattr(config, "RTL_433_BIN", exe, raising=False)

    # Global passthrough and per-radio args.
    monkeypatch.setattr(config, "RTL_433_ARGS", "-p 0", raising=False)
    monkeypatch.setattr(config, "RTL_433_CONFIG_PATH", "", raising=False)
    monkeypatch.setattr(config, "RTL_433_CONFIG_INLINE", "", raising=False)

    for slot, idx in enumerate(indices):
        radio = {
            "index": idx,
            "freq": "433.92M",
            "rate": "250k",
            "hop_interval": 0,
            "name": f"HWPassthrough{slot}",
            "id": f"99{slot}",
            "slot": slot,
            "args": "-g 0 -T 2",
        }

        cmd = build_rtl_433_command(radio)

        # Assert passthrough flags appear in the actual command.
        assert "-p" in cmd and "0" in cmd, f"Expected global -p 0 in cmd: {cmd}"
        assert "-g" in cmd and "0" in cmd, f"Expected per-radio -g 0 in cmd: {cmd}"
        assert "-T" in cmd and "2" in cmd, f"Expected per-radio -T 2 in cmd: {cmd}"

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if proc.returncode != 0:
            _skip_for_common_hw_errors(proc)

        assert proc.returncode == 0, (
            "rtl_433 failed with passthrough args\n"
            f"CMD: {cmd}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        )
