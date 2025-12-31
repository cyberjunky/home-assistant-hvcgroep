"""Data update coordinator for HVC Groep integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BAGID_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GARBAGE_ID_TO_TYPE,
    WASTE_URL,
)

_LOGGER = logging.getLogger(__name__)


class HVCGroepDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching HVC Groep data."""

    def __init__(
        self,
        hass: HomeAssistant,
        postal_code: str,
        house_number: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._postal_code = postal_code
        self._house_number = house_number
        self._bag_id: str | None = None
        self._session = async_get_clientsession(hass)

    @property
    def postal_code(self) -> str:
        """Return the postal code."""
        return self._postal_code

    @property
    def house_number(self) -> str:
        """Return the house number."""
        return self._house_number

    async def _get_bag_id(self) -> str | None:
        """Get the BAG ID using postal code and house number."""
        url = BAGID_URL.format(self._postal_code, self._house_number)
        _LOGGER.debug("Fetching BAG ID from: %s", url)

        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(url)
                response.raise_for_status()
                json_data = await response.json()

            if json_data and len(json_data) > 0:
                bag_id = json_data[0].get("bagId")
                _LOGGER.debug("Found BAG ID: %s", bag_id)
                return bag_id

            _LOGGER.error("No BAG ID found for %s-%s", self._postal_code, self._house_number)
            return None

        except TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching BAG ID: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching BAG ID: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from HVC Groep API."""
        # Get BAG ID if we don't have it yet
        if not self._bag_id:
            self._bag_id = await self._get_bag_id()
            if not self._bag_id:
                raise UpdateFailed("Could not retrieve BAG ID")

        url = WASTE_URL.format(self._bag_id)
        _LOGGER.debug("Fetching waste schedule from: %s", url)

        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(url)
                response.raise_for_status()
                json_data = await response.json()

        except TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching waste schedule: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching waste schedule: {err}") from err

        # Parse the waste schedule data
        result: dict[str, Any] = {
            "garbage": {},
            "pickup_today": [],
            "pickup_tomorrow": [],
        }

        today = datetime.today().date()
        tomorrow = today + timedelta(days=1)

        for item in json_data:
            pickup_date_str = item.get("ophaaldatum")
            if not pickup_date_str:
                continue

            waste_id = item.get("id")
            if waste_id not in GARBAGE_ID_TO_TYPE:
                _LOGGER.debug("Unknown waste type ID: %s", waste_id)
                continue

            garbage_type = GARBAGE_ID_TO_TYPE[waste_id]

            try:
                pickup_date = datetime.strptime(pickup_date_str, "%Y-%m-%d").date()
            except ValueError:
                _LOGGER.warning("Invalid date format: %s", pickup_date_str)
                continue

            days_until = (pickup_date - today).days

            _LOGGER.debug(
                "Garbage type: %s, pickup date: %s, days until: %d",
                garbage_type,
                pickup_date,
                days_until,
            )

            result["garbage"][garbage_type] = {
                "pickup_date": pickup_date,
                "days_until": days_until,
                "title": item.get("title", ""),
            }

            # Track items for today/tomorrow aggregate sensors
            if pickup_date == today:
                result["pickup_today"].append(garbage_type)
            elif pickup_date == tomorrow:
                result["pickup_tomorrow"].append(garbage_type)

        return result


async def validate_connection(
    hass: HomeAssistant, postal_code: str, house_number: str
) -> bool:
    """Validate the connection to HVC Groep API."""
    session = async_get_clientsession(hass)
    url = BAGID_URL.format(postal_code, house_number)

    try:
        async with async_timeout.timeout(10):
            response = await session.get(url)
            response.raise_for_status()
            json_data = await response.json()

        if json_data and len(json_data) > 0 and json_data[0].get("bagId"):
            return True

        return False

    except (TimeoutError, aiohttp.ClientError) as err:
        _LOGGER.error("Connection validation failed: %s", err)
        return False
