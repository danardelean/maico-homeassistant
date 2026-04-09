# Maico REC DUO WiFi - Home Assistant Integration

Custom Home Assistant integration for **Maico REC DUO 100/150 WiFi** ventilation and heat recovery devices.

## Features

- **Fan control**: Turn on/off, set fan speed (16 levels)
- **Operating modes**: Push/Pull, Free Cooling, Supply Only, Extract Only
- **Boost mode**: Timed high-speed ventilation with configurable duration
- **Sleep/Night mode**: Timed low-speed ventilation with configurable duration
- **Sensors**: Temperature, humidity, air quality, air flow (RPM), filter hours
- **Settings**: LED brightness, humidity threshold, air quality threshold
- **Maintenance**: Filter reset button, device reboot
- **Real-time updates**: WebSocket connection for instant state changes
- **Multi-device support**: Manages multiple ambients and devices

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots menu and select "Custom repositories"
3. Add this repository URL and select "Integration" as the category
4. Click "Install"
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/maico` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Maico REC DUO WiFi"
3. Open the login URL shown in your browser
4. Sign in with your Maico/REC VMC account credentials
5. After login, you'll be redirected to a URL like `myrecvmc://login?code=XXXX`
6. Copy the code value and paste it into the Home Assistant setup form

## Entities

For each REC DUO device, the integration creates:

| Entity Type | Name | Description |
|-------------|------|-------------|
| Fan | Ventilation | On/off and speed control |
| Sensor | Temperature | Air temperature (°C) |
| Sensor | Humidity | Relative humidity (%) |
| Sensor | Air Quality | Air quality index |
| Sensor | Air Flow | Fan speed (RPM) |
| Sensor | Filter Hours | Filter operating hours |
| Binary Sensor | Online | Device connectivity status |
| Binary Sensor | Filter Warning | Filter needs cleaning |
| Select | Operating Mode | Push/Pull, Extract, Supply, Free Cooling |
| Switch | Boost Mode | Timed boost ventilation |
| Switch | Sleep Mode | Timed night mode |
| Switch | Air Quality Threshold | AQS auto-control |
| Number | LED Brightness | Device LED level (1-5) |
| Number | Humidity Threshold | Hygro mode threshold (%) |
| Number | Low Speed | Quiet mode fan speed |
| Number | Boost Duration | Boost timer (minutes) |
| Number | Sleep Duration | Sleep timer (minutes) |
| Button | Clear Filter | Reset filter counter |
| Button | Reboot | Restart device |

## Automations

Example automations you can create:

- Turn on boost when bathroom humidity exceeds a threshold
- Activate night mode at bedtime
- Send a notification when the filter needs cleaning
- Adjust fan speed based on outdoor temperature

## Requirements

- Home Assistant 2024.1 or later
- Maico REC DUO 100 WiFi or REC DUO 150 WiFi device(s)
- Active Maico cloud account (same credentials used in the mobile app)
