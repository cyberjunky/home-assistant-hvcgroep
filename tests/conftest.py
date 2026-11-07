"""Fixtures for HVC Groep tests."""

from datetime import date, timedelta
from typing import Any

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.hvcgroep.const import (
    BAGID_URL,
    CONF_HOUSE_NUMBER,
    CONF_POSTAL_CODE,
    DOMAIN,
    WASTE_URL,
)

POSTAL_CODE = "1234AB"
HOUSE_NUMBER = "1"
BAG_ID = "0123456789"

ENTRY_DATA = {CONF_POSTAL_CODE: POSTAL_CODE, CONF_HOUSE_NUMBER: HOUSE_NUMBER}

BAGID_API = BAGID_URL.format(POSTAL_CODE, HOUSE_NUMBER)
WASTE_API = WASTE_URL.format(BAG_ID)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of the custom integration in all tests."""
    return


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"HVC Groep ({POSTAL_CODE})",
        data=dict(ENTRY_DATA),
        unique_id=f"{POSTAL_CODE}_{HOUSE_NUMBER}",
    )


def pickup(days: int) -> date:
    """Return the date `days` from today in Home Assistant's time zone."""
    return dt_util.now().date() + timedelta(days=days)


def waste_schedule() -> list[dict[str, Any]]:
    """Return a schedule: GFT today, plastic tomorrow, paper in 5 days."""
    return [
        {"id": 5, "title": "GFT", "ophaaldatum": pickup(0).isoformat()},
        {"id": 6, "title": "Plastic", "ophaaldatum": pickup(1).isoformat()},
        {"id": 3, "title": "Papier", "ophaaldatum": pickup(5).isoformat()},
        # Skipped: no pickup date, unknown waste type, malformed date
        {"id": 2, "title": "Restafval", "ophaaldatum": None},
        {"id": 999, "title": "Unknown", "ophaaldatum": pickup(2).isoformat()},
        {"id": 59, "title": "Reiniging", "ophaaldatum": "not-a-date"},
    ]


def mock_api(
    aioclient_mock: AiohttpClientMocker,
    *,
    bag: list[dict[str, Any]] | None = None,
    schedule: list[dict[str, Any]] | None = None,
) -> None:
    """Register the HVC Groep API responses."""
    aioclient_mock.get(BAGID_API, json=[{"bagId": BAG_ID}] if bag is None else bag)
    aioclient_mock.get(WASTE_API, json=waste_schedule() if schedule is None else schedule)
