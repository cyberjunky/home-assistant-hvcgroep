[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

# HVC Groep Custom Integration

A Home Assistant Custom Integration that fetches garbage pickup schedules for parts of The Netherlands serviced by the HVC Groep.

## Supported Features

- **GUI Configuration**: Easy setup through the Home Assistant UI
- **All Sensors Enabled**: All garbage types are automatically available (disable individual sensors in HA if needed)
- **Built-in Aggregate Sensors**: "Pickup Today" and "Pickup Tomorrow" sensors showing which bins are being collected
- **Translations**: Available in English and Dutch (NL)
- **YAML Migration**: Existing YAML configurations are automatically migrated

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

![Sensor Overview](screenshots/hvcgroep.png)

## Requirements

- Are you serviced by HVC Groep?
- Do you have a valid postal code and house number?

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cyberjunky&repository=home-assistant-hvcgroep&category=integration)

Alternatively:

1. Install [HACS](https://hacs.xyz) if not already installed
2. Search for "HVC Groep" in HACS
3. Click **Download**
4. Restart Home Assistant
5. Add via Settings → Devices & Services

### Manual Installation

1. Copy `custom_components/hvcgroep` to your `<config>/custom_components/` directory
2. Restart Home Assistant
3. Add via Settings → Devices & Services

## Configuration

### Adding the Integration

1. Navigate to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"HVC Groep"**
4. Enter your configuration:
   - **Postal Code**: Your postal code
   - **House Number**: Your house number

### Migrating from YAML

> **Note:** YAML configuration is deprecated as of v2.0.0

If you previously configured this integration in `configuration.yaml`, your settings will be **automatically imported** on your first restart after updating.

**Your old YAML config** (will be migrated):

```yaml
sensor:
  - platform: hvcgroep
    postcode: 1234AB
    huisnummer: 1
    resources:
      - gft
      - plastic
      - papier
      - restafval
      - reiniging
    date_format_default: '%d-%m-%Y'
    date_format_tomorrow: 'Morgen %d-%m-%Y'
    date_format_today: 'Vandaag %d-%m-%Y'
```

**After migration:**

1. Remove the YAML configuration from `configuration.yaml`
2. Manage all settings via **Settings** → **Devices & Services** → **HVC Groep** → **Configure**
3. Disable unwanted sensors through entity settings

### Date Format Options

After adding the integration, click **Configure** to customize how dates are displayed:

| Option | Description | Default |
|--------|-------------|---------|
| Default date format | Format for future dates | `%d-%m-%Y` |
| Today format | Format when pickup is today | `Today %d-%m-%Y` |
| Tomorrow format | Format when pickup is tomorrow | `Tomorrow %d-%m-%Y` |

#### Format Codes

Use Python [strftime format codes](https://strftime.org/):

| Code | Meaning | Example |
|------|---------|---------|
| `%d` | Day (zero-padded) | 03 |
| `%m` | Month (zero-padded) | 01 |
| `%Y` | Year (4-digit) | 2026 |
| `%A` | Full weekday name | Friday / Vrijdag |
| `%a` | Abbreviated weekday | Fri / Vr |
| `%B` | Full month name | January / januari |
| `%b` | Abbreviated month | Jan / jan |

> **Note:** Day and month names (`%A`, `%B`, `%a`, `%b`) are automatically localized based on your Home Assistant language setting.

#### Examples

| Format | Dutch HA | English HA |
|--------|----------|------------|
| `%d-%m-%Y` | 03-01-2026 | 03-01-2026 |
| `%A %d-%m-%Y` | Vrijdag 03-01-2026 | Friday 03-01-2026 |
| `%a %d %B` | Vr 03 januari | Fri 03 January |
| `Vandaag %A` | Vandaag Vrijdag | Vandaag Friday |
| `Tomorrow %d/%m` | Tomorrow 03/01 | Tomorrow 03/01 |

## Advanced Usage

### Automation Examples

Get notified when garbage will be collected:

```yaml
automation:
  - alias: "Notification Garbage Tomorrow"
    triggers:
      - trigger: state
        entity_id: sensor.hvc_groep_1234ab_pickup_tomorrow
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable', 'None'] }}"
    actions:
      - action: notify.mobile_app
        data:
          title: "Garbage Collection"
          message: "Tomorrow: {{ trigger.to_state.state }}"

  - alias: "Notification Garbage Today"
    triggers:
      - trigger: state
        entity_id: sensor.hvc_groep_1234ab_pickup_today
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable', 'None'] }}"
    actions:
      - action: notify.mobile_app
        data:
          title: "Garbage Collection"
          message: "Today: {{ trigger.to_state.state }}"
```

> **Note:** Replace `sensor.hvc_groep_1234ab_*` with your actual sensor entity IDs and `notify.mobile_app` with your notification service.

## Troubleshooting

### Common Issues

**Old YAML config not migrating:**

- Check Home Assistant logs for import errors
- Verify the YAML syntax is correct
- Manually add via UI if automatic import fails

**No sensors created:**

- Verify the postal code and house number are correct
- Check Home Assistant logs for connection errors

**No pickup dates:**

- Verify the postal code and house number are correct
- Check Home Assistant logs for connection errors

### Enable Debug Logging

Add the relevant lines below to the `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hvcgroep: debug
```

Alternatively, enable debug logging via the UI in **Settings** → **Devices & Services** → **HVC Groep** → **Enable debug logging**:

![Enable Debug Logging](screenshots/enabledebug.png)

Then perform any steps to reproduce the issue and disable debug logging again. It will download the relevant log file automatically.

## Development

Quick-start (from project root):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements_lint.txt
./scripts/lint    # runs pre-commit + vulture
# or: ruff check .
# to auto-fix: ruff check . --fix
```

## 💖 Support This Project

If you find this library useful for your projects, please consider supporting its continued development and maintenance:

### 🌟 Ways to Support

- **⭐ Star this repository** - Help others discover the project
- **💰 Financial Support** - Contribute to development and hosting costs
- **🐛 Report Issues** - Help improve stability and compatibility
- **📖 Spread the Word** - Share with other developers

### 💳 Financial Support Options

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

**Why Support?**

- Keeps the project actively maintained
- Enables faster bug fixes and new features
- Supports infrastructure costs (testing, AI, CI/CD)
- Shows appreciation for hundreds of hours of development

Every contribution, no matter the size, makes a difference and is greatly appreciated! 🙏

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

[releases-shield]: https://img.shields.io/github/release/cyberjunky/home-assistant-hvcgroep.svg?style=for-the-badge
[releases]: https://github.com/cyberjunky/home-assistant-hvcgroep/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/cyberjunky/home-assistant-hvcgroep.svg?style=for-the-badge
[commits]: https://github.com/cyberjunky/home-assistant-hvcgroep/commits/main
[license-shield]: https://img.shields.io/github/license/cyberjunky/home-assistant-hvcgroep.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-cyberjunky-blue.svg?style=for-the-badge
