"""Sensors for HVC Groep integration."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, ClassVar

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_POSTAL_CODE, DOMAIN, GARBAGE_TYPES
from .coordinator import HVCGroepDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# Sensor descriptions for garbage types
GARBAGE_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = tuple(
    SensorEntityDescription(
        key=key,
        translation_key=info["translation_key"],
        icon=info["icon"],
    )
    for key, info in GARBAGE_TYPES.items()
)

# Aggregate sensor descriptions
AGGREGATE_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="pickup_today",
        translation_key="pickup_today",
        icon="mdi:calendar-today",
    ),
    SensorEntityDescription(
        key="pickup_tomorrow",
        translation_key="pickup_tomorrow",
        icon="mdi:calendar-arrow-right",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HVC Groep sensors based on a config entry."""
    coordinator: HVCGroepDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Add garbage type sensors
    for description in GARBAGE_SENSOR_DESCRIPTIONS:
        entities.append(
            HVCGroepGarbageSensor(
                coordinator=coordinator,
                entry=entry,
                description=description,
            )
        )

    # Add aggregate sensors (today/tomorrow pickup)
    for description in AGGREGATE_SENSOR_DESCRIPTIONS:
        entities.append(
            HVCGroepAggregateSensor(
                coordinator=coordinator,
                entry=entry,
                description=description,
            )
        )

    async_add_entities(entities)


class HVCGroepBaseSensor(CoordinatorEntity[HVCGroepDataUpdateCoordinator], SensorEntity):
    """Base class for HVC Groep sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HVCGroepDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

        # Create unique ID
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Device info - group all sensors under one device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"HVC Groep ({entry.data[CONF_POSTAL_CODE]})",
            "manufacturer": "HVC Groep",
            "model": "Waste Collection",
            "configuration_url": "https://www.hvcgroep.nl",
        }


class HVCGroepGarbageSensor(HVCGroepBaseSensor):
    """Sensor for a specific garbage type pickup date."""

    # Day translations
    DAY_TRANSLATIONS: ClassVar[dict[str, dict[str, str]]] = {
        "nl": {"today": "Vandaag", "tomorrow": "Morgen"},
        "en": {"today": "Today", "tomorrow": "Tomorrow"},
    }

    def _get_language(self) -> str:
        """Get the configured language, defaulting to Dutch."""
        lang = self.coordinator.hass.config.language
        if lang and lang.startswith("en"):
            return "en"
        return "nl"

    def _get_days_until(self, pickup_date: date | None = None) -> int | None:
        """Calculate days until pickup dynamically from the pickup date."""
        if pickup_date is None:
            if not self.coordinator.data:
                return None
            garbage_data = self.coordinator.data.get("garbage", {})
            type_data = garbage_data.get(self.entity_description.key)
            if type_data:
                pickup_date = type_data.get("pickup_date")
            else:
                return None

        if pickup_date is None:
            return None

        today = date.today()
        return (pickup_date - today).days

    def _format_date(self, pickup_date: date, days_until: int) -> str:
        """Format date based on language setting, with today/tomorrow prefix."""
        lang = self._get_language()
        translations = self.DAY_TRANSLATIONS.get(lang, self.DAY_TRANSLATIONS["nl"])

        # For today/tomorrow, just return the translated word without date
        if days_until == 0:
            return translations["today"]
        elif days_until == 1:
            return translations["tomorrow"]

        # For future dates, return formatted date
        if lang == "en":
            return pickup_date.strftime("%m-%d-%Y")  # US format
        return pickup_date.strftime("%d-%m-%Y")  # Dutch/EU format

    @property
    def native_value(self) -> str | None:
        """Return the pickup date formatted according to language."""
        if not self.coordinator.data:
            return None

        garbage_data = self.coordinator.data.get("garbage", {})
        type_data = garbage_data.get(self.entity_description.key)

        if type_data:
            pickup_date = type_data.get("pickup_date")
            if pickup_date:
                # Calculate days_until dynamically for accurate today/tomorrow detection
                days_until = self._get_days_until(pickup_date)
                if days_until is not None:
                    return self._format_date(pickup_date, days_until)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        garbage_data = self.coordinator.data.get("garbage", {})
        type_data = garbage_data.get(self.entity_description.key)

        if type_data:
            pickup_date = type_data.get("pickup_date")
            # Calculate days_until dynamically
            days_until = self._get_days_until(pickup_date) if pickup_date else None

            if days_until is not None:
                lang = self._get_language()
                translations = self.DAY_TRANSLATIONS.get(lang, self.DAY_TRANSLATIONS["nl"])

                attrs = {
                    "days_until_pickup": days_until,
                }

                # Add translated day indicator for today/tomorrow
                if days_until == 0:
                    attrs["day"] = translations["today"]
                elif days_until == 1:
                    attrs["day"] = translations["tomorrow"]

                return attrs

        return {}


class HVCGroepAggregateSensor(HVCGroepBaseSensor):
    """Sensor showing what garbage is being picked up today or tomorrow."""

    # Human-readable names for garbage types per language
    GARBAGE_NAMES_NL: ClassVar[dict[str, str]] = {
        "gft": "Groene bak",
        "plastic": "Plastic",
        "papier": "Blauwe bak",
        "restafval": "Grijze bak",
        "reiniging": "Reiniging",
    }

    GARBAGE_NAMES_EN: ClassVar[dict[str, str]] = {
        "gft": "Green bin",
        "plastic": "Plastic",
        "papier": "Blue bin",
        "restafval": "Grey bin",
        "reiniging": "Cleaning",
    }

    # "None" translations
    NONE_VALUES: ClassVar[dict[str, str]] = {
        "nl": "Geen",
        "en": "None",
    }

    def _get_language(self) -> str:
        """Get the configured language, defaulting to Dutch since HVC Groep is a Dutch service."""
        lang = self.coordinator.hass.config.language
        # Only use English if explicitly set to English, otherwise default to Dutch
        if lang and lang.startswith("en"):
            return "en"
        return "nl"

    def _get_none_value(self) -> str:
        """Get the translated 'None' value."""
        lang = self._get_language()
        return self.NONE_VALUES.get(lang, "Geen")

    def _get_garbage_names(self) -> dict[str, str]:
        """Get the garbage names dictionary for the current language."""
        if self._get_language() == "en":
            return self.GARBAGE_NAMES_EN
        return self.GARBAGE_NAMES_NL

    @property
    def native_value(self) -> str:
        """Return the list of garbage types being picked up."""
        if not self.coordinator.data:
            return self._get_none_value()

        pickup_list = self.coordinator.data.get(self.entity_description.key, [])

        if not pickup_list:
            return self._get_none_value()

        # Build display string from human-readable names
        garbage_names = self._get_garbage_names()
        names = [garbage_names.get(g, g) for g in pickup_list]
        return " + ".join(names)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        pickup_list = self.coordinator.data.get(self.entity_description.key, [])

        return {
            "garbage_types": pickup_list,
            "count": len(pickup_list),
        }
