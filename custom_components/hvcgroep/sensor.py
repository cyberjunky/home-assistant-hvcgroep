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
import voluptuous as vol

import aiohttp
import asyncio
import async_timeout

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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

    trashdata = TrashData(hass, postcode, huisnummer)
    try:
        await trashdata.async_update()
    except ValueError as err:
        _LOGGER.error("Error while fetching data from HVCGroep: %s", err)
        return

    entities = []
    for resource in config[CONF_RESOURCES]:
        trash_type = resource.lower()
        name = default_name + "_" + trash_type
        id = TRASH_TYPES[resource][0]
        icon = TRASH_TYPES[resource][2]

        _LOGGER.debug("Adding HVCGroep sensor: {}, {}, {}, {}".format(name, trash_type, id, icon))
        entities.append(TrashSensor(trashdata, name, trash_type, id, icon))

    async_add_entities(entities, True)


# pylint: disable=abstract-method
class TrashData(object):
    """Handle HVCGroep object and limit updates."""

    def __init__(self, hass, postcode, huisnummer):
        """Initialize."""
        self._hass = hass
        self._postcode = postcode
        self._huisnummer = huisnummer
        self._bagid = None
        self._data = None


    async def _get_bagid(self):

        """Get the bagid using postcode and huisnummer."""
        try:
            websession = async_get_clientsession(self._hass)
            with async_timeout.timeout(5):
                response = await websession.get(self._build_bagid_url())
            _LOGGER.debug(
                "Response status from HVC bagid: %s", response.status
            ) 
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Cannot connect to HVC for bagid: %s", err)
            self._data = None
            return
        except Exception as err:
            _LOGGER.error("Error downloading bagid from HVC: %s", err)
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

        # try:
        #     json_data = requests.get(self._build_bagid_url(), timeout=5).json()
        #     self._bagid = json_data[0]["bagId"]
        #     _LOGGER.debug("Found BagId = %s", self._bagid)
        # except (requests.exceptions.RequestException) as error:
        #     _LOGGER.error("Unable to get BagId from HVCGroep: %s", error)

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
            websession = async_get_clientsession(self._hass)
            with async_timeout.timeout(5):
                response = await websession.get(self._build_waste_url())
            _LOGGER.debug(
                "Response status from HVC: %s", response.status
            ) 
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Cannot connect to HVC: %s", err)
            self._data = None
            return
        except Exception as err:
            _LOGGER.error("Error downloading bagid from HVC: %s", err)
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

    def __init__(self, trashdata, name, trash_type, id, icon):
        """Initialize the sensor."""
        self._trashdata = trashdata
        self._name = name
        self._trash_type = trash_type
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

        await self._trashdata.async_update()
        trashdata = self._trashdata.latest_data

        today = datetime.today()

        if trashdata:
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

            _LOGGER.debug("Device: {} State: {}".format(self._name, self._state))