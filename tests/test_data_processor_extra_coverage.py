import pytest

import data_processor
import config


class DummyMQTT:
    def __init__(self):
        self.calls = []

    # matches usage in data_processor.py
    def send_sensor(self, clean_id, field, value, dev_name, model, is_rtl=False):
        self.calls.append(
            {
                "clean_id": clean_id,
                "field": field,
                "value": value,
                "dev_name": dev_name,
                "model": model,
                "is_rtl": is_rtl,
            }
        )


def test_dispatch_reading_interval_zero_sends_immediately(monkeypatch):
    monkeypatch.setattr(config, "RTL_THROTTLE_INTERVAL", 0)

    mqtt = DummyMQTT()
    dp = data_processor.DataProcessor(mqtt)

    dp.dispatch_reading(
        clean_id="dev1",
        field="temp",
        value=12.34,
        dev_name="Bridge",
        model="ModelX",
        radio_name="RTL_0",
        radio_freq="433.92M",
    )

    assert len(mqtt.calls) == 1
    c = mqtt.calls[0]
    assert c["clean_id"] == "dev1"
    assert c["field"] == "temp"
    assert c["value"] == 12.34
    assert c["dev_name"] == "Bridge"
    assert c["model"] == "ModelX"
    assert c["is_rtl"] is True


def test_dispatch_reading_buffers_and_updates_meta(monkeypatch):
    monkeypatch.setattr(config, "RTL_THROTTLE_INTERVAL", 10)

    mqtt = DummyMQTT()
    dp = data_processor.DataProcessor(mqtt)

    # first write creates __meta__
    dp.dispatch_reading(
        clean_id="devA",
        field="humidity",
        value=50,
        dev_name="DeviceA",
        model="M1",
        radio_name="RTL_A",
        radio_freq="915M",
    )

    # second write should update radio/freq in existing __meta__
    dp.dispatch_reading(
        clean_id="devA",
        field="humidity",
        value=60,
        dev_name="DeviceA",
        model="M1",
        radio_name="RTL_A2",
        radio_freq="433M",
    )

    assert "devA" in dp.buffer
    meta = dp.buffer["devA"]["__meta__"]
    assert meta["name"] == "DeviceA"
    assert meta["model"] == "M1"
    assert meta["radio"] == "RTL_A2"
    assert meta["freq"] == "433M"
    assert dp.buffer["devA"]["humidity"] == [50, 60]


def test_start_throttle_loop_flushes_all_branches(monkeypatch, capsys):
    monkeypatch.setattr(config, "RTL_THROTTLE_INTERVAL", 1)

    mqtt = DummyMQTT()
    dp = data_processor.DataProcessor(mqtt)

    # Preload the buffer so the loop has work on its first iteration.
    # NOTE: use floats to reliably hit final_val.is_integer() path on Python 3.13
    with dp.lock:
        dp.buffer = {
            "dev_float_int": {
                "__meta__": {"name": "DevF", "model": "M", "radio": "RTL_F", "freq": "915M"},
                "temp": [1.0, 1.0],  # mean -> 1.0 -> is_integer -> int(1)
            },
            "dev_string": {
                "__meta__": {"name": "DevS", "model": "M", "radio": "RTL_S", "freq": "Unknown"},
                "status": ["OPEN", "CLOSED"],  # string path -> last value
            },
            "dev_mean_error": {
                "__meta__": {"name": "DevE", "model": "M", "radio": "RTL_E", "freq": "433.92M"},
                "weird": [1.0, "BAD"],  # numeric first elem, but mean() raises -> except -> last value
                "empty": [],            # empty list -> continue
            },
        }

    # Run exactly one iteration then stop: sleep once (process), sleep again (stop)
    calls = {"n": 0}

    def fake_sleep(_seconds):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise InterruptedError("stop loop")

    monkeypatch.setattr(data_processor.time, "sleep", fake_sleep)

    with pytest.raises(InterruptedError):
        dp.start_throttle_loop()

    # Verify sends happened
    assert mqtt.calls, "Expected send_sensor calls from flush"
    # temp averaged to int(1)
    assert any(c["clean_id"] == "dev_float_int" and c["field"] == "temp" and c["value"] == 1 for c in mqtt.calls)
    # string keeps last
    assert any(c["clean_id"] == "dev_string" and c["field"] == "status" and c["value"] == "CLOSED" for c in mqtt.calls)
    # mean error falls back to last
    assert any(c["clean_id"] == "dev_mean_error" and c["field"] == "weird" and c["value"] == "BAD" for c in mqtt.calls)

    out = capsys.readouterr().out
    # Consolidated heartbeat log should exist and include bracketed freq for non-Unknown
    assert "[THROTTLE] Flushed" in out
    assert "RTL_F[915M]" in out
    assert "RTL_E[433.92M]" in out
    # Unknown freq should NOT be bracketed (key should be just RTL_S)
    assert "RTL_S[" not in out


def test_start_throttle_loop_empty_buffer_continues(monkeypatch):
    monkeypatch.setattr(config, "RTL_THROTTLE_INTERVAL", 1)

    mqtt = DummyMQTT()
    dp = data_processor.DataProcessor(mqtt)

    calls = {"n": 0}

    def fake_sleep(_seconds):
        calls["n"] += 1
        # first pass: empty buffer -> continue
        # second sleep: stop
        if calls["n"] >= 2:
            raise InterruptedError("stop loop")

    monkeypatch.setattr(data_processor.time, "sleep", fake_sleep)

    with pytest.raises(InterruptedError):
        dp.start_throttle_loop()

    assert mqtt.calls == []


def test_throttle_battery_ok_uses_last_value_not_mean(monkeypatch):
    """battery_ok should not be averaged; last sample wins."""
    monkeypatch.setattr(config, "RTL_THROTTLE_INTERVAL", 1)

    mqtt = DummyMQTT()
    dp = data_processor.DataProcessor(mqtt)

    # Seed buffer with multiple battery_ok values that would differ from the mean.
    with dp.lock:
        dp.buffer = {
            "dev_batt": {
                "__meta__": {"name": "Dev", "model": "Model", "radio": "RTL", "freq": "433.92M"},
                "battery_ok": [1, 0, 1],  # mean=0.67, last=1
            }
        }

    calls = {"n": 0}

    def fake_sleep(_seconds):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise InterruptedError("stop loop")

    monkeypatch.setattr(data_processor.time, "sleep", fake_sleep)

    with pytest.raises(InterruptedError):
        dp.start_throttle_loop()

    assert any(c["clean_id"] == "dev_batt" and c["field"] == "battery_ok" and c["value"] == 1 for c in mqtt.calls)
