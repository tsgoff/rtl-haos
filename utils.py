# utils.py
"""
FILE: utils.py
DESCRIPTION:
  Shared helper functions used across the project.
  - clean_mac(): Sanitizes device IDs for MQTT topics.
  - calculate_dew_point(): Math formula to calculate Dew Point from Temp/Humidity.
  - get_system_mac(): Generates a unique ID for the bridge itself based on hardware.
  - validate_radio_config(): Checks for common configuration mistakes (Missing M, etc).
"""
import re
import math
import socket
import config

# Global cache
_SYSTEM_MAC = None

def get_system_mac():
    global _SYSTEM_MAC
    if _SYSTEM_MAC: 
        return _SYSTEM_MAC

    # 1. PREFERRED: Use Static ID from Config
    if config.BRIDGE_ID:
        _SYSTEM_MAC = config.BRIDGE_ID
        return _SYSTEM_MAC
    
    try:
        # 2. FALLBACK: Use Hostname (Dynamic on HAOS!)
        host_id = socket.gethostname()
        
        if not host_id:
            host_id = "rtl-bridge-default"
            
        _SYSTEM_MAC = host_id
        return _SYSTEM_MAC

    except Exception:
        return "rtl-bridge-error-id"

def clean_mac(mac):
    """Cleans up MAC/ID string for use in topic/unique IDs."""
    # Removes special characters to make it MQTT-safe
    cleaned = re.sub(r'[^A-Za-z0-9]', '', str(mac))
    return cleaned.lower() if cleaned else "unknown"

def calculate_dew_point(temp_c, humidity):
    """Calculates Dew Point (F) using Magnus Formula."""
    if temp_c is None or humidity is None:
        return None
    if humidity <= 0:
        return None 
    try:
        b = 17.62
        c = 243.12
        gamma = (b * temp_c / (c + temp_c)) + math.log(humidity / 100.0)
        dp_c = (c * gamma) / (b - gamma)
        return round(dp_c * 1.8 + 32, 1) # Return Fahrenheit
    except Exception:
        return None

def validate_radio_config(radio_conf):
    """
    Analyzes a radio configuration dictionary for common user errors.
    Returns a list of warning strings.
    """
    warnings = []
    
    # 1. Check Frequency for missing 'M'
    # rtl_433 defaults to Hz if no suffix is present.
    # 433.92 -> 433 Hz (Invalid). 433.92M -> 433,920,000 Hz (Valid).
    freq_str = str(radio_conf.get("freq", ""))
    frequencies = [f.strip() for f in freq_str.split(",")]
    
    for f in frequencies:
        # Regex: Matches pure numbers (int or float) with NO letters
        if re.match(r"^\d+(\.\d+)?$", f):
            val = float(f)
            # If value is < 1,000,000, it's almost certainly not Hz.
            # Typical RTL-SDR range is 24MHz+.
            if val < 1000000:
                warnings.append(
                    f"Frequency '{f}' has no suffix and will be read as Hz (impossible). "
                    f"Did you mean '{f}M'?"
                )

    # 2. Check Hop Interval vs Frequency Count
    # Hopping requires at least 2 frequencies.
    hop = int(radio_conf.get("hop_interval", 0))
    if hop > 0 and len(frequencies) < 2:
        warnings.append(
            f"Hop interval is set to {hop}s, but only 1 frequency provided ({freq_str}). "
            "Hopping will be ignored."
        )

    # 3. Check Sample Rate Suffix
    # 250 -> 250 Hz (Way too slow). 250k -> 250,000 Hz (Standard).
    rate = str(radio_conf.get("rate", ""))
    if re.match(r"^\d+$", rate):
        val = int(rate)
        if val < 1000000: # Assuming no one sets rate in raw Hz < 1M manually without good reason
            warnings.append(
                f"Sample rate '{rate}' has no suffix (e.g. 'k'). "
                f"Did you mean '{rate}k'?"
            )

    return warnings