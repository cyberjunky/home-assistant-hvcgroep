[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)  [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)

# HVC Groep Sensor Component
This is a Custom Component for Home-Assistant (https://home-assistant.io), it fetches garbage pickup dates for parts of The Netherlands using HVC Groep's REST API.


## Installation

### HACS - Recommended
- Have [HACS](https://hacs.xyz) installed, this will allow you to easily manage and track updates.
- Search for 'HVCGroep'.
- Click Install below the found integration.
- Configure using the configuration instructions below.
- Restart Home-Assistant.

### Manual
- Copy directory `custom_components/hvcgroep` to your `<config dir>/custom_components` directory.
- Configure with config below.
- Restart Home-Assistant.

## Usage
To use this component in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry

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

Configuration variables:

- **postcode** (*Required*): Your postal code.
- **huisnummer** (*Required*): Your house number.
- **resources** (*Required*): This section tells the component which types of garbage to get pickup dates for.

- **date_format_default** (Optional): Date format to use, if omitted %d-%m-%y is used
- **date_format_tomorrow** (Optional): Date format to use for tomorrow, if omitted 'Morgen %d-%m-%y' is used
- **date_format_today** (Optional): Date format to use for today, if omitted 'Vandaag %d-%m-%y' is used

You can create 2 extra sensors which hold the type of garbage to pickup today and tomorrow:
```yaml
# Example configuration.yaml entry

sensor:

  - platform: template
    sensors:
      afval_vandaag:
        friendly_name: "Vandaag"
        value_template: >-
          {% set afval = '' %}
          {% if is_state_attr('sensor.hvc_groep_groene_bak_gft', 'day', 'Vandaag') %}
          {% set afval = 'Groene Bak' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_blauwe_bak_papier', 'day', 'Vandaag') %}
            {% if afval|length %}
              {% set afval = afval + ' + Blauwe Bak' %}
            {% else %}
              {% set afval = 'Blauwe Bak' %}
            {% endif %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_plastic_en_verpakking', 'day', 'Vandaag') %}
            {% if afval|length %}
              {% set afval = afval + ' + Plastic' %}
            {% else %}
              {% set afval = 'Plastic' %}
            {% endif %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_grijze_bak_restafval', 'day', 'Vandaag') %}
            {% if afval|length %}
              {% set afval = afval + ' + Grijze Bak' %}
            {% else %}
              {% set afval = 'Grijze Bak' %}
            {% endif %}
          {% endif %}
          {% if afval|length %}
            {{afval}}
          {% else %}
            Geen
          {% endif %}

  - platform: template
    sensors:
      afval_morgen:
        friendly_name: "Morgen"
        value_template: >-
          {% set afval = '' %}
          {% if is_state_attr('sensor.hvc_groep_groene_bak_gft', 'day', 'Morgen') %}
          {% set afval = 'Groene Bak' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_blauwe_bak_papier', 'day', 'Morgen') %}
            {% if afval|length %}
              {% set afval = afval + ' + Blauwe Bak' %}
            {% else %}
              {% set afval = 'Blauwe Bak' %}
            {% endif %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_plastic_en_verpakking', 'day', 'Morgen') %}
            {% if afval|length %}
              {% set afval = afval + ' + Plastic' %}
            {% else %}
              {% set afval = 'Plastic' %}
            {% endif %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_grijze_bak_restafval', 'day', 'Morgen') %}
            {% if afval|length %}
              {% set afval = afval + ' + Grijze Bak' %}
            {% else %}
              {% set afval = 'Grijze Bak' %}
            {% endif %}
          {% endif %}
          {% if afval|length %}
            {{afval}}
          {% else %}
            Geen
          {% endif %}

```

And you can group them like so:
```yaml
# Example groups.yaml entry

Afval Ophaaldagen:
  - sensor.hvc_groep_blauwe_bak_papier
  - sensor.hvc_groep_groene_bak_gft
  - sensor.hvc_groep_plastic_en_verpakking
  - sensor.hvc_groep_grijze_bak_restafval
  - sensor.afval_vandaag
  - sensor.afval_morgen
  - sensor.hvc_groep_reiniging
  - sensor.afval_vandaag
  - sensor.afval_morgen
```
Thing to fix/add is multiple pickups per day for 'today' and 'tomorrow' sensor.

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

## Donation
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)
