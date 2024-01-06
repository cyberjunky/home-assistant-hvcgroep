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
        - reiniging
        date_format_default: '%d-%m-%Y'
        date_format_today: 'Vandaag %d-%m-%Y'
        date_format_tomorrow: 'Morgen %d-%m-%Y'
"""
import logging
from datetime import timedelta
from datetime import datetime
import voluptuous as vol
from typing import Final

import aiohttp
import asyncio
import async_timeout

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription
)
from homeassistant.const import (
    CONF_NAME, CONF_SCAN_INTERVAL, CONF_RESOURCES
    )
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

BAGID_URL = 'https://apps.hvcgroep.nl/rest/adressen/{0}-{1}'
WASTE_URL = 'https://apps.hvcgroep.nl/rest/adressen/{0}/afvalstromen'
_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=1)

SENSOR_PREFIX = 'HVC Groep'
CONST_POSTCODE = "postcode"
CONST_HUISNUMMER = "huisnummer"
CONF_FORMAT_DEFAULT = 'date_format_default'
CONF_FORMAT_TODAY = 'date_format_today'
CONF_FORMAT_TOMORROW = 'date_format_tomorrow'

SENSOR_LIST = {
    "gft": 5,
    "plastic": 6,
    "papier": 3,
    "restafval": 2,
    "reiniging": 59
}

SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    SensorEntityDescription(
        key="gft",
        name="Groene Bak GFT",
        icon="mdi:food-apple-outline"
    ),
    SensorEntityDescription(
        key="plastic",
        name="Plastic en Verpakking",
        icon="mdi:recycle"
    ),
    SensorEntityDescription(
        key="papier",
        name="Blauwe Bak Papier",
        icon="mdi:file"
    ),
    SensorEntityDescription(
        key="restafval",
        name="Grijze Bak Restafval",
        icon="mdi:delete-empty"
    ),
    SensorEntityDescription(
        key="reiniging",
        name="Reiniging",
        icon="mdi:liquid-spot"
    )
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=SENSOR_PREFIX): cv.string,
    vol.Required(CONST_POSTCODE): cv.string,
    vol.Required(CONST_HUISNUMMER): cv.string,
    vol.Required(CONF_RESOURCES, default=list(SENSOR_LIST)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_LIST)]),
    vol.Optional(CONF_FORMAT_DEFAULT, default='%d-%m-%Y'): cv.string,
    vol.Optional(CONF_FORMAT_TODAY, default='Vandaag %d-%m-%Y'): cv.string,
    vol.Optional(CONF_FORMAT_TOMORROW, default='Morgen %d-%m-%Y'): cv.string,
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the HVCGroep sensors."""

    scan_interval = config.get(CONF_SCAN_INTERVAL)
    postcode = config.get(CONST_POSTCODE)
    huisnummer = config.get(CONST_HUISNUMMER)
    default_name = config.get(CONF_NAME)
    date_formats = {
        'default': config.get(CONF_FORMAT_DEFAULT),
        'today': config.get(CONF_FORMAT_TODAY),
        'tomorrow': config.get(CONF_FORMAT_TOMORROW)
    }

    session = async_get_clientsession(hass)

    data = TrashData(session, postcode, huisnummer)
    try:
        await data.async_update()
    except ValueError as err:
        _LOGGER.error("Error while fetching data from HVCGroep: %s", err)
        return

    entities = []
    for description in SENSOR_TYPES:
        if description.key in config[CONF_RESOURCES]:
            sensor = TrashSensor(description, data, date_formats, default_name)
            entities.append(sensor)

    async_add_entities(entities, True)


# pylint: disable=abstract-method
class TrashData(object):
    """Handle HVCGroep object and limit updates."""

    def __init__(self, session, postcode, huisnummer):
        """Initialize."""

        self._session = session
        self._postcode = postcode
        self._huisnummer = huisnummer
        self._bagid = None
        self._data = None

    async def _get_bagid(self):
        """Get the bagid using postcode and huisnummer."""

        try:
            with async_timeout.timeout(5):
                response = await self._session.get(self._build_bagid_url())
            _LOGGER.debug(
                "Response status from HVC bagid: %s", response.status
            )
        except aiohttp.ClientError:
            _LOGGER.error("Cannot connect to HVC for bagid")
            self._data = None
            return
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occured while trying to get bagid from HVC")
            self._data = None
            return
        except Exception as err:
            _LOGGER.error("Unknown error occured while trying to get bagid from HVC: %s", err)
            self._data = None
            return

        try:
            json_data = await response.json()
            _LOGGER.debug("Data received from HVC: %s", json_data)
            self._bagid = json_data[0]["bagId"]
            _LOGGER.debug("Found BagId = %s", self._bagid)
        except Exception as err:
            _LOGGER.error("Cannot parse data from HVC: %s", err)
            self._data = None
            return

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
        if not self._bagid:
            await self._get_bagid()

        trashschedule = []
        try:
            with async_timeout.timeout(5):
                response = await self._session.get(self._build_waste_url())
            _LOGGER.debug(
                "Response status from HVC: %s", response.status
            )
        except aiohttp.ClientError:
            _LOGGER.error("Cannot connect to HVC")
            self._data = None
            return
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occured while trying to connect to HVC")
            self._data = None
            return
        except Exception as err:
            _LOGGER.error("Unknown error occured while downloading data from HVC: %s", err)
            self._data = None
            return

        try:
            json_data = await response.json()
            _LOGGER.debug("Data received from HVC: %s", json_data)
        except Exception as err:
            _LOGGER.error("Cannot parse data from HVC: %s", err)
            self._data = None
            return

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

    def __init__(self, description, data, date_formats, default_name):
        """Initialize the sensor."""
        self.entity_description = description
        self._data = data
        
        self._date_formats = date_formats
        self._default_name = default_name
        self._id = SENSOR_LIST[description.key]
        self._day = None
        self._datediff = None
        self._state = None

        self._type = self.entity_description.key
        self._attr_icon = self.entity_description.icon
        self._attr_name = self._default_name + " " + self.entity_description.name
        self._attr_unique_id = f"{self._default_name} {self._id}"

        self._discovery = False
        self._dev_id = {}

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of this device."""
        return {
            "day": self._day,
            "datediff": self._datediff
        }

    async def async_update(self):
        """Get the latest data and use it to update our sensor state."""

        await self._data.async_update()
        trash = self._data.latest_data

        today = datetime.today()

        if trash:
            for d in trash:
                pickupdate = d['date']
                datediff = (pickupdate - today).days + 1
                if d['id'] == self._id:
                    self._datediff = datediff
                    if datediff > 1:
                        self._state = pickupdate.strftime(self._date_formats['default'])
                        self._day = None
                    elif datediff == 1:
                        self._state = pickupdate.strftime(self._date_formats['tomorrow'])
                        self._day = "Morgen"
                    elif datediff <= 0:
                        self._state = pickupdate.strftime(self._date_formats['today'])
                        self._day = "Vandaag"
                    else:
                        self._state = None
                        self._day = None

            _LOGGER.debug("Device: {} State: {}".format(self._attr_name, self._state))
