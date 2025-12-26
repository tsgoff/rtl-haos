import rtl_manager


def test_safe_status_suffix_handles_empty_and_symbols():
    assert rtl_manager._safe_status_suffix(None) == "0"
    assert rtl_manager._safe_status_suffix("   ") == "0"
    assert rtl_manager._safe_status_suffix("a:b*c") == "a_b_c"


def test_discover_rtl_devices_missing_rtl_eeprom_does_not_crash(mocker, capsys):
    mocker.patch("rtl_manager.subprocess.run", side_effect=FileNotFoundError)

    devices = rtl_manager.discover_rtl_devices()
    out = capsys.readouterr().out.lower()

    assert devices == []
    assert "rtl_eeprom not found" in out
