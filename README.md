# Maico REC DUO WiFi - Home Assistant Integration

Custom Home Assistant integration for **Maico REC DUO 100/150 WiFi** ventilation and heat recovery devices.

## Features

- **Fan control**: Turn on/off, set fan speed (16 levels)
- **Operating modes**: Push/Pull, Raffrescamento, Sola estrazione, Sola immissione
- **Boost mode**: Timed high-speed ventilation with configurable duration
- **Sleep/Night mode**: Timed low-speed ventilation with configurable duration
- **Sensors**: Temperature, humidity, air quality, air flow (RPM), filter hours
- **Settings**: LED brightness, humidity threshold, air quality threshold, night mode speed
- **Maintenance**: Filter reset button, device reboot with confirmation
- **Real-time updates**: WebSocket connection for instant state changes (minimal API traffic)
- **Multi-device support**: Manages multiple ambients and devices
- **Startup sentinel filtering**: Ignores bogus 888.8 readings during device startup

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots menu and select **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Click **Install**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/maico` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Maico REC DUO WiFi**
3. Enter your Maico account credentials:
   - **Username**: Your Maico account username (same as the mobile app)
   - **Password**: Your Maico account password
   - **Client Secret**: The Cognito client secret (contact the developer or extract from the mobile app)
4. Click **Submit**
5. The integration will authenticate, discover your devices, and create all entities

## Entities

For each REC DUO device, the integration creates:

| Entity Type | Name | Description |
|-------------|------|-------------|
| Fan | Ventilation | On/off and speed control (1-16 levels) |
| Sensor | Temperature | Air temperature (°C) |
| Sensor | Humidity | Relative humidity (%) |
| Sensor | Air Quality | Air quality index |
| Sensor | Air Flow | Fan speed (RPM) |
| Sensor | Filter Hours | Filter operating hours |
| Sensor | Filter Threshold | Filter cleaning threshold (hours) |
| Sensor | Firmware Version | Current firmware |
| Binary Sensor | Online | Device connectivity status |
| Binary Sensor | Filter Warning | Filter needs cleaning |
| Binary Sensor | Master Device | Master/slave role |
| Select | Operating Mode | Push/Pull, Raffrescamento, Sola estrazione, Sola immissione |
| Switch | Boost Mode | Timed boost ventilation |
| Switch | Sleep Mode | Timed night mode |
| Switch | Air Quality Threshold | AQS auto-control |
| Number | LED Brightness | Device LED level (1-5) |
| Number | Humidity Threshold | Hygro mode threshold (40-100%) |
| Number | Night Mode Speed | Night mode fan speed (1-16) |
| Number | Boost Duration | Boost timer (minutes) |
| Number | Sleep Duration | Sleep timer (minutes) |
| Button | Clear Filter | Reset filter counter |
| Button | Reboot | Restart device |

## Dashboard

A sample dashboard YAML is included in the repository using Mushroom cards and Plotly Graph Card for interactive charts. See `maico_dashboard_remote.yaml` for a ready-to-use example.

Required custom cards (install via HACS):
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)
- [Plotly Graph Card](https://github.com/dbuezas/lovelace-plotly-graph-card)

## Automations

Example automations you can create:

- Turn on boost when bathroom humidity exceeds a threshold
- Activate night mode at bedtime
- Send a notification when the filter needs cleaning
- Adjust fan speed based on outdoor temperature

## API Traffic

The integration uses WebSocket for real-time updates and only falls back to REST polling when the WebSocket connection is lost. This minimizes AWS API traffic to near-zero during normal operation.

## Requirements

- Home Assistant 2024.1 or later
- Maico REC DUO 100 WiFi or REC DUO 150 WiFi device(s)
- Active Maico cloud account (same credentials used in the mobile app)
- Cognito client secret (provided separately)
