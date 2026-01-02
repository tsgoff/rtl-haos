# Configuration

This page summarizes the main configuration entry points for RTL-HAOS.

- **Home Assistant Add-on users:** configure via **Settings → Add-ons → RTL-HAOS → Configuration**.
- **Developers / standalone runs:** see `.env.example` for environment variable configuration.
- **Full schema:** see `config.yaml` (authoritative list of all options and defaults).

---

## Home Assistant Add-on

In Home Assistant: **Settings → Add-ons → RTL-HAOS → Configuration**.

### Common options

```yaml
# MQTT
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_user: ""
mqtt_pass: ""
mqtt_topic_prefix: rtl_433

# Logging
log_level: INFO
```

### Utility meters (gas + electric)

RTL-HAOS supports Itron-style utility meters (e.g., `ERT-SCM`, `SCMplus`) and publishes Home Assistant MQTT discovery entities for totals.

**Electric meters**
- Published as **Energy (kWh)**.
- Values are scaled from **hundredths of kWh → kWh** (÷100) when the meter is identified as electric.

**Gas meters**
- Published as **Gas (ft³)** by default (**raw** totals).
- Optional: publish in **CCF** (hundred cubic feet) by setting:

```yaml
gas_unit: ft3   # default
# gas_unit: ccf # optional (publishes totals in CCF by dividing ft³ by 100)
```

> **Upgrade note (v1.1.13 → v1.1.14):** gas totals may appear to increase by ~100× compared to v1.1.13 if you were previously seeing CCF-like values while labeled as ft³. This is expected when switching to raw ft³. See `CHANGELOG.md` → v1.1.14 → “Migration from v1.1.13”.

### Auto-config vs manual `rtl_config`

Most users can leave RTL in auto mode:

```yaml
rtl_auto: true
rtl_auto_frequency: 915000000
rtl_auto_sample_rate: 1024000
rtl_auto_gain: 0
```

If you want full control (multiple radios, fixed protocols, hopping, etc.), set `rtl_config` explicitly. The full shape and defaults are defined in `config.yaml`.

Example (manual radio with protocol filter):

```yaml
rtl_config:
  - name: equascan
    freq: 868.95M
    rate: 250k
    # Optional: limit rtl_433 decoders via -R
    # Comma- or space-separated ints, e.g. "104,105".
    protocols: "104,105"
```


### Advanced: full rtl_433 passthrough

RTL-HAOS can pass **arbitrary rtl_433 flags** and/or a full **rtl_433 config file**. This is the most flexible way to tune reception (gain/ppm/AGC), constrain decoders, or use tuner settings.

**Global passthrough (applies to all radios):**

```yaml
# Extra flags appended to every rtl_433 invocation
rtl_433_args: '-g 40 -p 0 -t "direct_samp=1"'

# Optional: provide an rtl_433 config file via -c
# In the HA add-on, relative paths resolve under /share (e.g. /share/rtl_433.conf).
rtl_433_config_path: "rtl_433.conf"

# Or inline config content (RTL-HAOS writes it to /tmp and passes -c /tmp/...)
rtl_433_config_inline: |
  -g 40
  -p 0
  -R 104
  -R 105
```

**Per-radio passthrough (overrides/extends the global settings):**

```yaml
rtl_config:
  - name: utility
    freq: 868.95M
    rate: 250k

    # Optional: override which RTL-SDR this radio uses (-d accepts index/serial/Soapy selectors)
    device: ":00000001"

    # Extra flags for this radio only
    args: '-g 25 -t "biastee=1"'

    # Optional: per-radio config file or inline config (takes precedence over global)
    config_path: "utility.conf"
    # config_inline: |
    #   -g 25
    #   -R 104
```

Notes:
- RTL-HAOS prefers **JSON output**. If you add extra `-F` outputs, RTL-HAOS will ignore non-JSON lines, but your logs may be noisier.
- You can still use the simpler `protocols:` field for a quick `-R` filter.

### Device filtering

You can restrict which decoded devices become entities using whitelist/blacklist rules:

```yaml
rtl_whitelist:
  - "Acurite-5n1*"
  - "AmbientWeather*"
rtl_blacklist:
  - "EcoWitt-WH40*"
```

(Exact matching behavior is defined in code; see `config.yaml` for the option names.)

### Multiple RTL-SDR dongles with duplicate serials

If you have multiple RTL-SDRs that report the same USB serial (common with some dongles), RTL-HAOS may suffix duplicates (e.g., `00000001-1`, `00000001-2`) to keep them distinct.  
If you use manual `rtl_config` device IDs, make sure they match what the add-on logs show at startup.

---

## Environment variables (dev / standalone)

For non–Home Assistant usage or development runs, you can configure via environment variables. See `.env.example` for the complete list.

---
