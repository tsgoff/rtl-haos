# RTL-433 to Home Assistant Bridge


This project turns one or more RTL-SDR dongles into a Home Assistant-friendly sensor bridge. It also acts as a **System Monitor**, reporting the host machine's CPU, RAM, Disk, and Temperature stats to Home Assistant.

It:

- Runs `rtl_433` and parses its JSON output
- Normalizes and flattens sensor data
- Optionally averages/buffers readings to reduce noise
- Publishes everything to an MQTT broker using **Home Assistant MQTT Discovery**
- Publishes **system/bridge diagnostics** (CPU, RAM, disk, host model, IP, device list)

The goal is a “drop-in” bridge: plug in RTL-SDR(s), run this script, and watch devices appear in Home Assistant with clean names, units, and icons.

## ✨ Features

* **MQTT Auto-Discovery:** Sensors appear automatically in Home Assistant without manual YAML configuration.
* **Field metadata**: units, device_class, icons, friendly names (for HA) 
* **System monitor**:
  - CPU %, RAM %, disk %, CPU temp, script memory
  - Bridge uptime, OS version, model, IP
  - Count/list of active RF devices
* **Dew point calculation** derived from temperature + humidity
* **Filtering:** Built-in Whitelist and Blacklist support to ignore neighbor's sensors.
* **Multi-Radio Support:** Can manage multiple SDR dongles on different frequencies simultaneously.
* **Data Averaging:** Buffers and averages sensor readings over a set interval (e.g., 30s) to reduce database noise.

---

## 📂 Project Layout

- `rtl_mqtt_bridge.py` – main entry point; runs rtl_433, buffering, and system monitor threads.  
- `config.py` – user-editable configuration (radios, filters, MQTT settings, throttle interval).  
- `mqtt_handler.py` – wraps Paho MQTT client, handles HA discovery and publishing.  
- `field_meta.py` – maps field names → (unit, device_class, icon, friendly name).  
- `system_monitor.py` – system monitor loop (bridge stats + hardware metrics).  
- `sensors_system.py` – low-level system stats using `psutil`.  
- `utils.py` – shared helpers: MAC handling, dew point math, system MAC ID.  

---


---

## 🛠️ Requirements

* **Hardware:** An RTL-SDR USB Dongle (e.g., RTL-SDR Blog V3, Nooelec).
* **Software:** * Python 3.7+
    * [rtl_433](https://github.com/merbanan/rtl_433) (Must be installed and accessible in your system path).

---

## 🚀 Installation

1.  **Install System Dependencies** (Debian/Ubuntu/Raspberry Pi):
    ```bash
    # 1. update and install system dependencies
    sudo apt update
    sudo apt install rtl-433 git python3 pip3 python3-venv
    
    # 2. Create a virtual environment named 'venv' in your current directory
    python3 -m venv venv
    
    # 3. Activate the virtual environment
    source venv/bin/activate
    
    # Your command prompt will change to show you are in the 'venv' environment.
    
    # 4. Install the packages from your requirements file
    pip3 install -r requirements.txt
    ```

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/jaronmcd/rtl-haos.git
    cd rtl-haos
    ```

---

## ⚙️ Configuration

1.  **Create your config file:**
    ```bash
    cp config.example.py config.py
    ```

2.  **Edit `config.py`** to match your environment:
    * **MQTT_SETTINGS:** Set your Broker IP, username, and password.
    * **RTL_CONFIG:** Set your radio frequency (default `433.92M`).
    * **RTL_THROTTLE_INTERVAL:** Set how many seconds to average data (default `30`).

---

## ▶️ Usage

Run the bridge manually to test:

```bash
python3 rtl_mqtt_bridge.py
```

### Expected Output
You should see logs indicating the bridge is connected and processing data:

```text
[STARTUP] Connecting to MQTT Broker at 192.168.1.100...
[MQTT] Connected Successfully.
[RTL] Starting Weather Radio on 433.92M...
[THROTTLE] Averaging data every 30 seconds.
[STARTUP] Hardware Monitor (psutil) initialized.

 -> TX Acurite-5n1 (1234) [temperature]: 72.3
 -> TX Acurite-5n1 (1234) [humidity]: 45
 -> TX Generic-Device (A1B2) [pressure_hpa]: 1013
```

---

## 🧩 Home Assistant Setup

1.  Ensure you have an MQTT Broker (like Mosquitto) installed.
2.  Ensure the **MQTT Integration** is active in Home Assistant.
3.  Start this script.
4.  Go to **Settings > Devices & Services > MQTT**. 
5.  Your devices (and the Bridge System Monitor) will appear automatically.

---

## 🤖 Running as a Service (Optional)

To keep the script running in the background on Linux, create a systemd service.

1.  Create file: `sudo nano /etc/systemd/system/rtl-bridge.service`
2.  Paste the following (adjust paths to match your user):

```ini
[Unit]
Description=RTL-433 MQTT Bridge
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rtl-haos
ExecStart=/usr/bin/python3 /home/pi/rtl-haos/rtl_mqtt_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3.  Enable and start:
    ```bash
    sudo systemctl enable rtl-bridge.service
    sudo systemctl start rtl-bridge.service
    ```


