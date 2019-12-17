[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)  [![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)

# HVC Groep Sensor Component
This component fetches garbage pickup dates for parts of The Netherlands using HVC Groep's REST API.

## Home-Assistant Custom Component
This is a Custom Component for Home-Assistant (https://home-assistant.io)

### Installation

- Copy directory `custom_components/hvcgroep` to your `<config dir>/custom_components` directory.
- Configure with config below.
- Restart Home-Assistant.

### Usage
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
```

Configuration variables:

- **postcode** (*Required*): Your postal code.
- **huisnummer** (*Required*): Your house number.
- **resources** (*Required*): This section tells the component which types of garbage to get pickup dates for.

You can create 2 extra sensors which hold the type of garbage to pickup today and tomorrow:
```
  - platform: template
    sensors:
      afval_vandaag:
        friendly_name: 'Vandaag'
        value_template: >-
          {% if is_state_attr('sensor.hvc_groep_gft', 'day', 'Vandaag') %}
          {% set gft = 'Groene Bak' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_papier', 'day', 'Vandaag') %}
          {% set papier = 'Blauwe Bak' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_plastic', 'day', 'Vandaag') %}
          {% set plastic = 'Plastic' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_restafval', 'day', 'Vandaag') %}
          {% set restafval = 'Grijze Bak' %}
          {% endif %}
             {{gft}} {{papier}} {{plastic}} {{restafval}}

  - platform: template
    sensors:
      afval_morgen:
        friendly_name: 'Morgen'
        value_template: >-
          {% if is_state_attr('sensor.hvc_groep_gft', 'day', 'Morgen') %}
          {% set gft = 'Groene Bak' %}
          {% elif is_state_attr('sensor.hvc_groep_papier', 'day', 'Morgen') %}
          {% set papier = 'Blauwe Bak' %}
          {% if is_state_attr('sensor.hvc_groep_plastic', 'day', 'Morgen') %}
          {% set plastic = 'Plastic' %}
          {% endif %}
          {% if is_state_attr('sensor.hvc_groep_restafval', 'day', 'Morgen') %}
          {% endif %}
          {% set restafval = 'Grijze Bak' %}
          {% endif %}
             {{gft}} {{papier}} {{plastic}} {{restafval}}
```

And you can group them like so:
```
Afval Ophaaldagen:
  - sensor.hvc_groep_gft
  - sensor.hvc_groep_papier
  - sensor.hvc_groep_plastic
  - sensor.hvc_groep_restafval
  - sensor.afval_vandaag
  - sensor.afval_morgen
```
Thing to fix/add is multiple pickups per day for 'today' and 'tomorrow' sensor.

### Screenshots

![alt text](https://https://github.com/cyberjunky/home-assistant-hvcgroep/blob/master/screenshots/hvcgroep.png?raw=true "Screenshot HVCGroep")

### Changes
* first release for hacs

### Donation
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/cyberjunkynl/)
