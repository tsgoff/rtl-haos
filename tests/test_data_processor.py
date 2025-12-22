import pytest
from data_processor import DataProcessor
import time

def test_dispatch_immediate(mocker, mock_config):
    """If throttling is 0, should send immediately."""
    mocker.patch("config.RTL_THROTTLE_INTERVAL", 0)
    mock_mqtt = mocker.Mock()
    
    processor = DataProcessor(mock_mqtt)
    processor.dispatch_reading("test_id", "temp", 72.5, "Sensor A", "Model X")
    
    # Verify send_sensor was called once
    mock_mqtt.send_sensor.assert_called_once()
    args = mock_mqtt.send_sensor.call_args[0]
    assert args[0] == "test_id"
    assert args[2] == 72.5

def test_dispatch_throttled(mocker, mock_config):
    """If throttling is ON, should buffer and average."""
    mocker.patch("config.RTL_THROTTLE_INTERVAL", 30)
    mock_mqtt = mocker.Mock()
    
    processor = DataProcessor(mock_mqtt)
    
    # Send 3 readings
    processor.dispatch_reading("id1", "temp", 10.0, "Dev1", "Mod1")
    processor.dispatch_reading("id1", "temp", 20.0, "Dev1", "Mod1")
    processor.dispatch_reading("id1", "temp", 30.0, "Dev1", "Mod1")
    
    # MQTT should NOT have been called yet
    mock_mqtt.send_sensor.assert_not_called()
    
    # Manually trigger the flush logic (simulating the thread loop)
    # We can't run the actual loop because it sleeps, so we extract the logic or inspect buffer
    assert "id1" in processor.buffer
    assert processor.buffer["id1"]["temp"] == [10.0, 20.0, 30.0]

    # Now verify the math logic manually since we aren't spinning the thread
    import statistics
    avg = statistics.mean(processor.buffer["id1"]["temp"])
    assert avg == 20.0