"""Sensors for HVC Groep integration."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
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
        device_class=SensorDeviceClass.DATE,
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

    @property
    def native_value(self) -> date | None:
        """Return the pickup date."""
        if not self.coordinator.data:
            return None

        garbage_data = self.coordinator.data.get("garbage", {})
        type_data = garbage_data.get(self.entity_description.key)

        if type_data:
            return type_data.get("pickup_date")

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        garbage_data = self.coordinator.data.get("garbage", {})
        type_data = garbage_data.get(self.entity_description.key)

        if type_data:
            days_until = type_data.get("days_until", 0)
            attrs = {
                "days_until_pickup": days_until,
            }

            # Add day indicator for today/tomorrow
            if days_until == 0:
                attrs["day"] = "today"
            elif days_until == 1:
                attrs["day"] = "tomorrow"

            return attrs

        return {}


class HVCGroepAggregateSensor(HVCGroepBaseSensor):
    """Sensor showing what garbage is being picked up today or tomorrow."""

    # Human-readable names for garbage types (Dutch)
    GARBAGE_NAMES: ClassVar[dict[str, str]] = {
        "gft": "Groene bak",
        "plastic": "Plastic",
        "papier": "Blauwe bak",
        "restafval": "Grijze bak",
        "reiniging": "Reiniging",
    }

    @property
    def native_value(self) -> str | None:
        """Return the list of garbage types being picked up."""
        if not self.coordinator.data:
            return None

        pickup_list = self.coordinator.data.get(self.entity_description.key, [])

        if not pickup_list:
            return None

        # Build display string from human-readable names
        names = [self.GARBAGE_NAMES.get(g, g) for g in pickup_list]
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
