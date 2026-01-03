"""The HVC Groep integration."""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_HOUSE_NUMBER, CONF_POSTAL_CODE, DOMAIN
from .coordinator import HVCGroepDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# This integration is configured via config entries only
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Legacy YAML configuration schema
LEGACY_PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Optional("name"): cv.string,
        vol.Required("postcode"): cv.string,
        vol.Required("huisnummer"): cv.string,
        vol.Optional("resources"): vol.All(cv.ensure_list),
        vol.Optional("date_format_default"): cv.string,
        vol.Optional("date_format_today"): cv.string,
        vol.Optional("date_format_tomorrow"): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HVC Groep integration from YAML."""
    hass.data.setdefault(DOMAIN, {})

    # Check for legacy YAML configuration under sensor platform
    if "sensor" in config:
        for sensor_config in config["sensor"]:
            if sensor_config.get("platform") == DOMAIN:
                # Found legacy YAML configuration, trigger import
                _LOGGER.warning(
                    "Configuration of HVC Groep via YAML is deprecated. "
                    "Your configuration has been imported. Please remove the "
                    "hvcgroep sensor platform from your configuration.yaml"
                )
                hass.async_create_task(
                    hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "import"},
                        data={
                            CONF_POSTAL_CODE: sensor_config.get("postcode", ""),
                            CONF_HOUSE_NUMBER: sensor_config.get("huisnummer", ""),
                        },
                    )
                )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HVC Groep from a config entry."""
    coordinator = HVCGroepDataUpdateCoordinator(
        hass,
        postal_code=entry.data[CONF_POSTAL_CODE],
        house_number=entry.data[CONF_HOUSE_NUMBER],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    # Currently at version 1, no migration needed yet
    # Add migration logic here for future versions

    return True
