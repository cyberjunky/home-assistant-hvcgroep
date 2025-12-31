[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)  [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)

# HVC Groep Sensor Component

This is a Custom Component for Home-Assistant (https://home-assistant.io) that fetches garbage pickup dates for parts of The Netherlands using HVC Groep's REST API.

## Features

- **GUI Configuration**: Easy setup through the Home Assistant UI
- **All Sensors Enabled**: All garbage types are automatically available (disable individual sensors in HA if needed)
- **Built-in Aggregate Sensors**: "Pickup Today" and "Pickup Tomorrow" sensors showing which bins are being collected
- **Translations**: Available in English and Dutch (NL)
- **YAML Migration**: Existing YAML configurations are automatically migrated

## Installation

### HACS - Recommended

1. Have [HACS](https://hacs.xyz) installed
2. Search for 'HVC Groep'
3. Click Install below the found integration
4. Restart Home-Assistant
5. Go to **Settings** → **Devices & Services** → **Add Integration** → search for "HVC Groep"

### Manual

1. Copy directory `custom_components/hvcgroep` to your `<config dir>/custom_components` directory
2. Restart Home-Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration** → search for "HVC Groep"

## Configuration

### GUI Setup (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "HVC Groep"
4. Enter your postal code and house number
5. Click **Submit**

That's it! All sensors will be automatically created.

### Migration from YAML

If you have an existing YAML configuration, it will be automatically imported when you restart Home Assistant. You will see a notification confirming the migration. After migration, you can remove the old YAML configuration from your `configuration.yaml`.

## Sensors

The integration creates the following sensors:

### Garbage Pickup Sensors

| Sensor | Description | Icon |
|--------|-------------|------|
| Green bin (organic) | GFT/organic waste pickup date | 🍎 |
| Plastic and packaging | Plastic waste pickup date | ♻️ |
| Blue bin (paper) | Paper waste pickup date | 📄 |
| Grey bin (residual waste) | Residual waste pickup date | 🗑️ |
| Cleaning | Street cleaning date | 💧 |

Each sensor shows the next pickup date and includes the following attributes:
- `days_until_pickup`: Number of days until the next pickup
- `day`: Set to "today" or "tomorrow" when applicable

### Aggregate Sensors

| Sensor | Description |
|--------|-------------|
| Pickup today | Shows which garbage types are being collected today |
| Pickup tomorrow | Shows which garbage types are being collected tomorrow |

These sensors replace the need for template sensors - the integration handles the "today/tomorrow" logic automatically.

## Multiple Addresses

You can configure multiple addresses by adding the integration multiple times through the GUI. Each address will create its own set of sensors grouped under a device.

## Screenshots

![alt text](https://github.com/cyberjunky/home-assistant-hvcgroep/blob/master/screenshots/hvcgroep.png?raw=true "Screenshot HVCGroep")

## Debugging

Add the relevant lines below to the `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hvcgroep: debug
```

## Changelog

### Version 2.0.0
- Added GUI configuration via config flow
- Added automatic YAML migration
- Added "Pickup Today" and "Pickup Tomorrow" aggregate sensors
- Added English and Dutch translations
- All sensors enabled by default (no resource selection needed)
- Removed date format settings (using device_class date for proper formatting)
- Modernized to use DataUpdateCoordinator pattern
- Improved error handling and connection validation

## Donation

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)
