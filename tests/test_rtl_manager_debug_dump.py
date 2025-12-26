import io
import json
import sys

import rtl_manager


def test_debug_dump_packet_prints_plan_and_stubs(mocker, capsys):
    """Covers rtl_manager._debug_dump_packet (reverse-engineering helper)."""

    raw_line = (
        '{"model":"Neptune-R900","id":"Meter1","consumption":12345,'
        '"temperature_F":68.0,"humidity":50,"nested":{"a":1}}\n'
    )

    data_raw = json.loads(raw_line)

    # Simulate the "processed" dict after rtl_loop mutations (consumption deleted,
    # plus an unknown field to trigger FIELD_META stubs).
    data_processed = {
        "model": "Neptune-R900",
        "id": "Meter1",
        "temperature_F": 68.0,
        "humidity": 50,
        "nested": {"a": 1},
        "alien_field": 7,
    }

    # Capture RAW_JSON output (debug dump writes this to sys.__stdout__ directly).
    raw_buf = io.StringIO()
    mocker.patch.object(sys, "__stdout__", raw_buf)

    # Make derived dew point deterministic.
    mocker.patch.object(rtl_manager, "calculate_dew_point", return_value=12.3)

    # Provide a tiny FIELD_META so we get a mix of supported + unsupported fields.
    mocker.patch(
        "field_meta.FIELD_META",
        {
            "temperature": ("°F", "temperature", "mdi:thermometer", "Temperature"),
            "humidity": ("%", "humidity", "mdi:water-percent", "Humidity"),
            "meter_reading": ("gal", "water", "mdi:water", "Meter Reading"),
            "dew_point": ("°F", "temperature", "mdi:weather-fog", "Dew Point"),
        },
    )

    rtl_manager._debug_dump_packet(
        raw_line=raw_line,
        data_raw=data_raw,
        data_processed=data_processed,
        radio_name="RTL0",
        radio_freq="433.92M",
        model="Neptune-R900",
        clean_id="meter1",
    )

    out = capsys.readouterr().out

    # Sanity: header + markers
    assert "[JSONDUMP]" in out
    assert "RAW_JSON_BEGIN" in out
    assert "PUBLISH plan" in out

    # Ensure raw JSON is printed to sys.__stdout__ exactly once (copy/paste friendly)
    assert raw_buf.getvalue().strip() == raw_line.strip()

    # Unsupported fields should produce FIELD_META stubs
    assert "FIELD_META stubs" in out
    assert '"alien_field"' in out
