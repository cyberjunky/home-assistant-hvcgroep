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

from .const import (
    CONF_DATE_FORMAT_DEFAULT,
    CONF_DATE_FORMAT_TODAY,
    CONF_DATE_FORMAT_TOMORROW,
    CONF_POSTAL_CODE,
    DEFAULT_DATE_FORMAT,
    DEFAULT_DATE_FORMAT_TODAY,
    DEFAULT_DATE_FORMAT_TOMORROW,
    DOMAIN,
    GARBAGE_TYPES,
)
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

    # Hardcoded translations for day and month names to avoid blocking I/O from babel
    DAY_NAMES: ClassVar[dict[str, list[str]]] = {
        "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "nl": ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"],
        "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        "fr": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
    }

    DAY_ABBR: ClassVar[dict[str, list[str]]] = {
        "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "nl": ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"],
        "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "fr": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
    }

    MONTH_NAMES: ClassVar[dict[str, list[str]]] = {
        "en": ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"],
        "nl": ["januari", "februari", "maart", "april", "mei", "juni",
               "juli", "augustus", "september", "oktober", "november", "december"],
        "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
               "Juli", "August", "September", "Oktober", "November", "Dezember"],
        "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
               "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    }

    MONTH_ABBR: ClassVar[dict[str, list[str]]] = {
        "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "nl": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
        "de": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "fr": ["jan", "fév", "mar", "avr", "mai", "jun", "jul", "aoû", "sep", "oct", "nov", "déc"],
    }

    def _get_date_format(self, format_key: str, default: str) -> str:
        """Get date format from options or return default."""
        return self._entry.options.get(format_key, default)

    def _get_language(self) -> str:
        """Get language code from HA language setting."""
        lang = self.coordinator.hass.config.language
        _LOGGER.debug("HA language setting: %s", lang)
        if lang and lang.startswith("nl"):
            return "nl"
        elif lang and lang.startswith("de"):
            return "de"
        elif lang and lang.startswith("fr"):
            return "fr"
        return "en"

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
        """Format date using configured format strings with locale support."""
        if days_until == 0:
            fmt = self._get_date_format(
                CONF_DATE_FORMAT_TODAY, DEFAULT_DATE_FORMAT_TODAY
            )
        elif days_until == 1:
            fmt = self._get_date_format(
                CONF_DATE_FORMAT_TOMORROW, DEFAULT_DATE_FORMAT_TOMORROW
            )
        else:
            fmt = self._get_date_format(
                CONF_DATE_FORMAT_DEFAULT, DEFAULT_DATE_FORMAT
            )

        # Check if format contains locale-sensitive patterns (%A, %B, %a, %b)
        locale_patterns = ["%A", "%B", "%a", "%b"]
        if any(p in fmt for p in locale_patterns):
            lang = self._get_language()
            result = fmt

            # weekday() returns 0=Monday, 6=Sunday
            if "%A" in result:
                day_names = self.DAY_NAMES.get(lang, self.DAY_NAMES["en"])
                result = result.replace("%A", day_names[pickup_date.weekday()])
            if "%a" in result:
                day_abbr = self.DAY_ABBR.get(lang, self.DAY_ABBR["en"])
                result = result.replace("%a", day_abbr[pickup_date.weekday()])

            # month is 1-indexed, list is 0-indexed
            if "%B" in result:
                month_names = self.MONTH_NAMES.get(lang, self.MONTH_NAMES["en"])
                result = result.replace("%B", month_names[pickup_date.month - 1])
            if "%b" in result:
                month_abbr = self.MONTH_ABBR.get(lang, self.MONTH_ABBR["en"])
                result = result.replace("%b", month_abbr[pickup_date.month - 1])

            # Apply remaining strftime patterns
            return pickup_date.strftime(result)

        return pickup_date.strftime(fmt)

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
                return {
                    "days_until_pickup": days_until,
                }

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
