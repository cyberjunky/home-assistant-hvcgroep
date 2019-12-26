"""
Support for reading trash pickup dates for HVC groep areas.

configuration.yaml

sensor:
  - platform: hvcgroep
    postcode: 1234AB
    huisnummer: 1
    resources:
      - gft
      - plastic
      - papier
      - restafval
"""
import logging
from datetime import timedelta
from datetime import datetime
import requests
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_SCAN_INTERVAL, CONF_RESOURCES
    )
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

BAGID_URL = 'https://apps.hvcgroep.nl/rest/adressen/{0}-{1}'
WASTE_URL = 'https://apps.hvcgroep.nl/rest/adressen/{0}/afvalstromen'
_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)

DEFAULT_NAME = 'HVC Groep'
CONST_POSTCODE = "postcode"
CONST_HUISNUMMER = "huisnummer"

# Predefined types and id's
TRASH_TYPES = {
    'gft': [5, 'Groene Bak GFT', 'mdi:food-apple-outline'],
    'plastic': [6, 'Plastic en Verpakking', 'mdi:recycle'],
    'papier': [3, 'Blauwe Bak Papier', 'mdi:file'],
    'restafval': [2, 'Grijze Bak Restafval', 'mdi:delete-empty'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONST_POSTCODE): cv.string,
    vol.Required(CONST_HUISNUMMER): cv.string,
    vol.Required(CONF_RESOURCES, default=list(TRASH_TYPES)):
        vol.All(cv.ensure_list, [vol.In(TRASH_TYPES)]),
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the HVCGroep sensors."""

    scan_interval = config.get(CONF_SCAN_INTERVAL)
    postcode = config.get(CONST_POSTCODE)
    huisnummer = config.get(CONST_HUISNUMMER)
    default_name = config.get(CONF_NAME)

    data = TrashData(postcode, huisnummer)
    try:
        await data.async_update()
    except ValueError as err:
        _LOGGER.error("Error while fetching data from HVCGroep: %s", err)
        return

    entities = []
    for resource in config[CONF_RESOURCES]:
        trash_type = resource.lower()
        name = default_name + "_" + trash_type
        id = TRASH_TYPES[resource][0]
        icon = TRASH_TYPES[resource][2]

        _LOGGER.debug("Adding HVCGroep sensor: {}, {}, {}, {}".format(trash_type, name, id, icon))
        entities.append(TrashSensor(data, trash_type, name, id, icon))

    async_add_entities(entities, True)


# pylint: disable=abstract-method
class TrashData(object):
    """Handle HVCGroep object and limit updates."""

    def __init__(self, postcode, huisnummer):
        """Initialize."""
        self._postcode = postcode
        self._huisnummer = huisnummer
        self._bagid = None
        self._data = None

        """Get the bagid using postcode and huisnummer."""
        try:
            json_data = requests.get(self._build_bagid_url(), timeout=5).json()
            self._bagid = json_data[0]["bagId"]
            _LOGGER.debug("Found BagId = %s", self._bagid)
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to get BagId from HVCGroep: %s", error)
    
    def _build_bagid_url(self):
        """Build the URL for the requests."""
        url = BAGID_URL.format(self._postcode, self._huisnummer)
        _LOGGER.debug("Bagid fetch URL: %s", url)
        return url

    def _build_waste_url(self):
        """Build the URL for the requests."""
        url = WASTE_URL.format(self._bagid)
        _LOGGER.debug("Waste fetch URL: %s", url)
        return url

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the afvalstromen data."""
        trashschedule = []
        try:
            json_data = requests.get(self._build_waste_url(), timeout=5).json()
            _LOGGER.debug("Afvalstromen fetched data = %s", json_data)
        except requests.exceptions.RequestException:
            _LOGGER.error("Unable to get afvalstromen data from HVCGroep: %s", error)
            self._data = None
            return False

        """Parse the afvalstromen data."""
        try:
            for afval in json_data:
                if afval['ophaaldatum'] != None:
                    _LOGGER.debug("Afvalstromen id: %s Type: %s Datum: %s", afval['id'], afval['title'], afval['ophaaldatum'])
                    trash = {}
                    trash['id'] = afval['id']
                    trash['title'] = afval['title']
                    trash['date'] = datetime.strptime(afval['ophaaldatum'], '%Y-%m-%d')
                    trashschedule.append(trash)
            self._data = trashschedule
        except ValueError as err:
            _LOGGER.error("Cannot parse the afvalstomen data %s", err.args)
            self._data = None
            return False


class TrashSensor(Entity):
    """Representation of a HVCGroep Sensor."""

    def __init__(self, data, trash_type, name, id, icon):
        """Initialize the sensor."""
        self._data = data
        self._trash_type = trash_type
        self._name = name
        self._id =  id
        self._icon = icon

        self._day = None
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        return {
            "day": self._day,
        }

    async def async_update(self):
        """Get the latest data and use it to update our sensor state."""

        await self._data.async_update()
        if not self._data:
            _LOGGER.error("Didn't receive data from TOON")
            return

        trashdata = self._data.latest_data
        today = datetime.today()

        for d in trashdata:
            pickupdate = d['date']
            datediff = (pickupdate - today).days + 1
            if d['id'] == self._id:
                if datediff > 1:
                    self._state = pickupdate.strftime('%d-%m-%Y')
                    self._day = None
                elif datediff == 1:
                    self._state = pickupdate.strftime('Morgen %d-%m-%Y')
                    self._day = "Morgen"
                elif datediff <= 0:
                    self._state = pickupdate.strftime('Vandaag %d-%m-%Y')
                    self._day = "Vandaag"
                else:
                    self._state = None
                    self._day = None

        _LOGGER.debug("Device id: {} State: {}".format(self._id, self._state))