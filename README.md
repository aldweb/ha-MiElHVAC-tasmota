# Tasmota MiElHVAC Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/aldweb/ha-tasmota-mielhvac.svg)](https://github.com/aldweb/ha-tasmota-mielhvac/releases)
[![License](https://img.shields.io/github/license/aldweb/ha-tasmota-mielhvac.svg)](LICENSE)

<img src="images/mitsubishi_heat_pump.png" align="left" width="300" style="margin-right: 20px; margin-bottom: 20px;">
Home Assistant integration for **Mitsubishi Electric heat pumps** controlled by Tasmota's MiElHVAC driver.

This integration automatically discovers and creates climate entities for your HVAC devices, seamlessly linking them to your existing Tasmota devices.
<br clear="all" />

## Features

- 🔍 **Automatic Discovery** - Detects MiElHVAC devices via MQTT automatically
- 🔗 **Device Linking** - Climate entities appear under your Tasmota devices
- 🌡️ **Full Climate Control** - Temperature, modes, fan speed, and swing control
- 🏠 **Local Control** - All communication via local MQTT (no cloud required)
- 🔄 **State Persistence** - Remembers settings after Home Assistant restarts
- 🌍 **Multi-language** - English and French UI translations included

## Supported Features

### HVAC Modes
- Off
- Auto
- Cool
- Dry
- Heat
- Fan Only

### Fan Speeds
- Auto
- Quiet
- Speed 1-4

### Swing Control
- **Vertical**: Auto, Up, Up-Middle, Center, Down-Middle, Down, Swing
- **Horizontal**: Auto, Left, Left-Middle, Center, Right-Middle, Right, Swing

### Temperature Control
- Range: 10°C - 31°C
- Precision: 0.5°C steps

## Prerequisites

### Hardware
- **ESP32 or ESP8266 device** running Tasmota
- **Mitsubishi Electric heat pump** with CN105 connector
- **JST PA 5-pin connector (2.0mm pitch)** to interface with CN105

For complete hardware setup including wiring diagrams and CN105 pinout, see:
- [Integration with Home Assistant via Tasmota (Archive)](https://web.archive.org/web/20240314034821/https://isaiahchia.com/2022/06/)
- [Hacking A Mitsubishi Heat Pump Part 1](https://chrdavis.github.io/hacking-a-mitsubishi-heat-pump-Part-1/)

### Software
- Home Assistant 2023.1 or newer
- **Tasmota firmware with MiElHVAC driver enabled**
  - Pre-compiled Tasmota32 firmware available at [MiElHVAC Tasmota Display Driver](https://github.com/aldweb/MiElHVAC-tasmota-display-driver)
  - Or compile your own using [TasmoCompiler](https://github.com/benzino77/tasmocompiler) with `#define USE_MIEL_HVAC`
- MQTT broker (e.g., Mosquitto) configured in Home Assistant

**Note:** This Home Assistant integration works with both ESP32 and ESP8266. The [MiElHVAC Display Driver](https://github.com/aldweb/MiElHVAC-tasmota-display-driver) (Berry-based web UI) requires ESP32 only, but is optional.

### Tasmota Configuration

Your Tasmota device must:

1. **Have MiElHVAC driver active**
   - The driver should publish HVAC data to `tele/{topic}/SENSOR`

2. **Be connected to your MQTT broker**
   - Same broker as Home Assistant

3. **Have discovery enabled** (recommended)
   ```
   SetOption19 0
   ```

4. **Have a configured Device Name**
   - Set in Tasmota: **Configuration** → **Configure Other** → **Device Name**
   - Example: "Living Room AC" or "Bedroom HVAC"

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on **Integrations**
3. Click the three dots menu (top right) → **Custom repositories**
4. Add repository:
   - **URL**: `https://github.com/aldweb/ha-tasmota-mielhvac`
   - **Category**: Integration
5. Click **Add**
6. Search for "Tasmota MiElHVAC" in HACS
7. Click **Download**
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub](https://github.com/aldweb/ha-tasmota-mielhvac/releases)
2. Extract the `tasmota_mielhvac` folder
3. Copy it to your Home Assistant `custom_components` directory:
   ```
   config/
   └── custom_components/
       └── tasmota_mielhvac/
   ```
4. Restart Home Assistant

## Configuration

### 1. Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Tasmota MiElHVAC"
4. Click on it and follow the setup dialog
5. Click **Submit**

That's it! No configuration needed - the integration will automatically discover your devices.

### 2. Verify Discovery

Check the logs to confirm your devices were discovered:

**Settings** → **System** → **Logs**

Look for messages like:
```
Discovered MiElHVAC device: tasmota_hvac (Temperature: 21.5°C) - Living Room AC
```

### 3. Check Your Devices

Go to **Settings** → **Devices & Services** → **MQTT**

Your Tasmota devices should now have a **climate entity** (HVAC) alongside their other entities.

## Usage

### Basic Control

Once discovered, you can control your HVAC through:

1. **Lovelace UI** - Use the standard Thermostat card
2. **Home Assistant App** - Full mobile control
3. **Automations** - Create climate-based automations
4. **Voice Assistants** - Control via Alexa, Google Assistant, etc.

## MQTT Topics

The integration listens to and publishes on standard Tasmota MQTT topics:

### Subscribed Topics (Listening)

| Topic | Purpose |
|-------|---------|
| `tele/{topic}/SENSOR` | Current temperature and humidity |
| `tele/{topic}/HVACSETTINGS` | HVAC state (mode, target temp, fan, swing) |
| `tele/{topic}/LWT` | Device availability (Online/Offline) |
| `tasmota/discovery/+/config` | Tasmota device discovery (for MAC and name) |

### Published Topics (Commands)

| Topic | Purpose | Example Payload |
|-------|---------|-----------------|
| `cmnd/{topic}/HVACSetHAMode` | Set HVAC mode | `heat`, `cool`, `auto` |
| `cmnd/{topic}/HVACSetTemp` | Set target temperature | `22` |
| `cmnd/{topic}/HVACSetFanSpeed` | Set fan speed | `auto`, `quiet`, `1`, `2`, `3`, `4` |
| `cmnd/{topic}/HVACSetSwingV` | Set vertical swing | `auto`, `up`, `up_middle`, `center`, `down_middle`, `down`, `swing` |
| `cmnd/{topic}/HVACSetSwingH` | Set horizontal swing | `auto`, `left`, `left_middle`, `center`, `right_middle`, `right`, `split`, `swing` |

## Troubleshooting

### Device Not Discovered

**Check these items:**

1. **MQTT Connection**
   - Verify Tasmota is connected to MQTT broker
   - Check MQTT broker logs for messages from your device

2. **MiElHVAC Data**
   - Use MQTT Explorer to check if `tele/{topic}/SENSOR` contains `MiElHVAC` data
   - The payload should include at least `Temperature`

3. **Home Assistant Logs**
   - Check for discovery messages or errors
   - Look for "Discovered MiElHVAC device" or error messages

4. **Tasmota Device Name**
   - Set a unique Device Name in Tasmota configuration
   - Restart Tasmota after changing the name

### Climate Entity Not Linked to Tasmota Device

This usually happens if Tasmota discovery is disabled.

**Solution:**

In Tasmota console, run:
```
SetOption19 0
Restart 1
```

### Commands Not Working

1. **Check MQTT topics in logs**
   - Verify commands are being published

2. **Test manually in Tasmota**
   - In Tasmota console, try: `HVACSetTemp 22`
   - If this doesn't work, the issue is with the Tasmota driver, not this integration

3. **Verify device is online**
   - Check LWT status in MQTT Explorer: `tele/{topic}/LWT` should be "Online"

### Multiple Entities Created

If you see duplicate climate entities:

1. Remove all duplicate entities via UI
2. Restart Home Assistant
3. The integration will recreate them correctly

## Enhanced Web Interface

For an enhanced Tasmota web interface with interactive controls (temperature adjustment, mode/fan/swing selectors), check out the companion Berry driver:

**[MiElHVAC Tasmota Display Driver](https://github.com/aldweb/MiElHVAC-tasmota-display-driver)**

This optional Berry script adds a full-featured web UI directly in your Tasmota interface. Note: Requires ESP32 (Berry scripting not available on ESP8266).

## Advanced Configuration

### Custom Device Names

Device names come from Tasmota's "Device Name" setting. To customize:

1. In Tasmota web UI: **Configuration** → **Configure Other**
2. Set **Device Name** to your preferred name
3. Restart Tasmota
4. In Home Assistant, remove and recreate the integration

### Horizontal Swing Control

Horizontal swing is available as an attribute:

```yaml
service: mqtt.publish
data:
  topic: cmnd/your_topic/HVACSetSwingH
  payload: left
```

Or use it in automations:
```yaml
action:
  - service: mqtt.publish
    data:
      topic: cmnd/{{ state_attr('climate.living_room_ac_hvac', 'friendly_name').lower() }}/HVACSetSwingH
      payload: swing
```

## Technical Details

### Architecture

```
┌─────────────────┐
│  Tasmota Device │
│  (ESP + HVAC)   │
└────────┬────────┘
         │ MQTT
         │
┌────────▼────────────────────┐
│    MQTT Broker              │
│    (Mosquitto)              │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────────────┐
│Tasmota│ │Tasmota MiElHVAC │
│Integr.│ │   Integration   │
└───┬───┘ └──┬──────────────┘
    │        │
    └───┬────┘
        │
┌───────▼──────────┐
│  Home Assistant  │
│  Climate Entity  │
└──────────────────┘
```

### Discovery Flow

1. Tasmota publishes device info to `tasmota/discovery/{MAC}/config`
2. Integration caches device MAC address and name
3. Tasmota publishes HVAC data to `tele/{topic}/SENSOR`
4. Integration detects MiElHVAC data
5. Climate entity is created and linked to Tasmota device via MAC address
6. Entity appears under the Tasmota device in Home Assistant

### Data Flow

**Temperature Updates:**
- Tasmota publishes current temp every TelePeriod (default 5 minutes)
- Integration updates Home Assistant immediately

**Commands:**
- User changes setting in Home Assistant
- Integration publishes MQTT command
- Tasmota sends command to HVAC
- Tasmota publishes new state
- Home Assistant updates entity

## Support

### Documentation
- [Installation Guide](INSTALLATION_GUIDE.md) - Detailed setup instructions
- [Technical Documentation](TECHNICAL_SOLUTION.md) - Architecture details
- [Examples](EXAMPLES_AND_TESTS.md) - MQTT examples and testing

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/aldweb/ha-tasmota-mielhvac/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aldweb/ha-tasmota-mielhvac/discussions)
- **Home Assistant Community**: [Forum Thread](https://community.home-assistant.io/)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

### Related Projects
- [MiElHVAC Tasmota Display Driver](https://github.com/aldweb/MiElHVAC-tasmota-display-driver) - Berry script for web UI controls and display

### Technology
- [Home Assistant](https://www.home-assistant.io/) - Open source home automation
- [Tasmota](https://tasmota.github.io/) - ESP firmware with MiElHVAC driver
- [SwiCago](https://github.com/SwiCago/HeatPump) - Original Mitsubishi protocol reverse engineering

### Development
- Created by [@aldweb](https://github.com/aldweb)
- Inspired by the Tasmota and Home Assistant communities

## Changelog

### Version 1.0.0 (2026-02-04)
- Initial public release
- Automatic device discovery via Tasmota MQTT discovery
- Full climate control support
- Device linking to existing Tasmota devices
- Multi-language UI (English, French)
- HACS compatible

---

**Enjoy your automated climate control! 🌡️❄️🔥**
