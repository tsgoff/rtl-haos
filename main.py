#!/usr/bin/env python3
"""
FILE: main.py
DESCRIPTION:
  The main executable script.
  - Checks dependencies.
  - Starts MQTT Handler.
  - Starts Data Processor (Throttling).
  - Starts RTL Managers (Radios).
  - Starts System Monitor.
"""
import builtins
from datetime import datetime
import sys
import threading
import time
import importlib.util
import subprocess
import os

# --- 1. GLOBAL LOGGING & COLOR SETUP ---
# Standard ANSI Colors for HAOS
c_blue = "\033[1;34m"    # Bold Blue (Logo)
c_purple = "\033[1;35m"  # Bold Purple (Subtitle)
c_green = "\033[32m"     # Green (INFO tag)
c_reset = "\033[0m"

_original_print = builtins.print

def timestamped_print(*args, **kwargs):
    """
    Replica of HAOS Logging format:
    [HH:MM:SS] INFO: <Message>
    We color 'INFO:' green to match the supervisor style.
    """
    now = datetime.now().strftime("%H:%M:%S")
    
    # Construct the prefix with color
    prefix = f"[{now}] {c_green}INFO:{c_reset}"
    
    # Convert all args to string to avoid format errors
    msg = " ".join(map(str, args))
    
    # Use original print, flushing immediately
    _original_print(f"{prefix} {msg}", flush=True, **kwargs)

# Override the built-in print
builtins.print = timestamped_print
# ------------------------------------

# --- PRE-FLIGHT DEPENDENCY CHECK ---
def check_dependencies():
    if not subprocess.run(["which", "rtl_433"], capture_output=True).stdout:
        print("CRITICAL: 'rtl_433' binary not found. Please install it.")
        sys.exit(1)

    if importlib.util.find_spec("paho") is None:
        print("CRITICAL: Python dependency 'paho-mqtt' not found.")
        sys.exit(1)

check_dependencies()

import config
from mqtt_handler import HomeNodeMQTT
from utils import get_system_mac
from system_monitor import system_stats_loop

# New Imports from Split Files
from data_processor import DataProcessor
from rtl_manager import rtl_loop, discover_rtl_devices

def get_version():
    """Retrieves the version string from config.yaml."""
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.yaml")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                for line in f:
                    if line.strip().startswith("version:"):
                        ver = line.split(":", 1)[1].strip().replace('"', '').replace("'", "")
                        return f"v{ver}"
    except Exception:
        pass
    return "Unknown"

def show_logo(version):
    """Prints the ASCII logo (Blue) and Subtitle (Purple) using sys.stdout."""
    logo = r"""
  ____  _____  _         _   _    _    ___  ____  
 |  _ \|_   _|| |       | | | |  / \  / _ \/ ___| 
 | |_) | | |  | |  ___  | |_| | / _ \| | | \___ \ 
 |  _ <  | |  | | |___| |  _  |/ ___ \ |_| |___) |
 |_| \_\ |_|  |_____|   |_| |_/_/   \_\___/|____/ 
    """
    
    # We construct the whole block with color codes
    banner = (
        f"{c_blue}{logo}{c_reset}\n"
        f"   {c_purple}>>> RTL-SDR Bridge for Home Assistant ({version}) <<<{c_reset}\n"
        f"   --------------------------------------------------\n"
    )
    
    # Write directly to stdout buffer to ensure color isn't stripped by 'print'
    sys.stdout.write(banner)
    sys.stdout.flush()

def main():
    ver = get_version()
    show_logo(ver)
    time.sleep(3)

    # 2. START MQTT
    mqtt_handler = HomeNodeMQTT(version=ver)
    mqtt_handler.start()

    # 3. START DATA PROCESSOR
    processor = DataProcessor(mqtt_handler)
    threading.Thread(target=processor.start_throttle_loop, daemon=True).start()

    # 4. GET SYSTEM IDENTITY
    sys_id = get_system_mac().replace(":", "").lower() 
    sys_model = config.BRIDGE_NAME
    sys_name = f"{sys_model} ({sys_id})"

    # --- NEW: HARDWARE MAPPING ---
    print("[STARTUP] Scanning USB bus for RTL-SDR devices...")
    detected_devices = discover_rtl_devices()
    
    # Create a map: "102" -> 0, "101" -> 1
    serial_to_index = {}
    if detected_devices:
        for d in detected_devices:
            if 'id' in d and 'index' in d:
                serial_to_index[str(d['id'])] = d['index']
        print(f"[STARTUP] Hardware Map: {serial_to_index}")
    else:
        print("[STARTUP] Warning: No hardware detected during scan.")

    # 5. START RTL RADIO THREADS
    rtl_config = getattr(config, "RTL_CONFIG", None)

    if rtl_config:
        # --- MANUAL MODE (Advanced) ---
        print(f"[STARTUP] Loading {len(rtl_config)} radios from manual config.")
        
        for radio in rtl_config:
            target_id = radio.get("id") 
            if target_id: target_id = str(target_id).strip()
            
            if target_id and target_id in serial_to_index:
                idx = serial_to_index[target_id]
                radio['index'] = idx
                r_name = radio.get("name", "Unknown")
                print(f"[STARTUP] Matched Config '{r_name}' (Serial {target_id}) to Physical Index {idx}")
            else:
                if target_id:
                     print(f"[STARTUP] Warning: Configured Serial {target_id} not found in scan. Driver may fail.")

            threading.Thread(
                target=rtl_loop,
                args=(radio, mqtt_handler, processor, sys_id, sys_model),
                daemon=True,
            ).start()
            
            print("[STARTUP] Staggering next radio start by 5 seconds...")
            time.sleep(5)
            
    else:
        # --- AUTO MODE (Simple) ---
        if detected_devices:
            target_radio = detected_devices[0]
            
            print(f"[STARTUP] Auto-detected {len(detected_devices)} radios.")
            print(f"[STARTUP] Unconfigured Mode: Selecting first device only ({target_radio['name']}).")
            
            radio_setup = {
                "freq": config.RTL_DEFAULT_FREQ,
                "hop_interval": config.RTL_DEFAULT_HOP_INTERVAL,
                "rate": config.RTL_DEFAULT_RATE
            }
            radio_setup.update(target_radio)

            threading.Thread(
                target=rtl_loop,
                args=(radio_setup, mqtt_handler, processor, sys_id, sys_model),
                daemon=True,
            ).start()
                
        else:
            # FALLBACK
            print("[STARTUP] No serials detected. Defaulting to generic device '0'.")
            auto_radio = {
                "name": "RTL_auto", 
                "id": "0",
                "freq": config.RTL_DEFAULT_FREQ,             
                "hop_interval": config.RTL_DEFAULT_HOP_INTERVAL,
                "rate": config.RTL_DEFAULT_RATE
            }

            threading.Thread(
                target=rtl_loop,
                args=(auto_radio, mqtt_handler, processor, sys_id, sys_model),
                daemon=True,
            ).start()

    # 6. START SYSTEM MONITOR
    threading.Thread(
        target=system_stats_loop, 
        args=(mqtt_handler, sys_id, sys_model), 
        daemon=True
    ).start()

    # 7. MAIN LOOP
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping MQTT...")
        mqtt_handler.stop()

if __name__ == "__main__":
    main()