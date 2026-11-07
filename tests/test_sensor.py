"""Tests for the HVC Groep sensors."""

import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.hvcgroep.const import (
    CONF_DATE_FORMAT_DEFAULT,
    CONF_DATE_FORMAT_TODAY,
    CONF_DATE_FORMAT_TOMORROW,
)

from .conftest import mock_api, pickup


async def _setup(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    **kwargs,
) -> None:
    mock_api(aioclient_mock, **kwargs)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, entry: MockConfigEntry, key: str):
    """Return the state of the sensor with the given description key."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", "hvcgroep", f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None, key
    return hass.states.get(entity_id)


async def test_sensors_created(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """All five waste types plus the two aggregate sensors are created."""
    await _setup(hass, mock_config_entry, aioclient_mock)

    entries = er.async_entries_for_config_entry(er.async_get(hass), mock_config_entry.entry_id)
    assert {e.unique_id.removeprefix(f"{mock_config_entry.entry_id}_") for e in entries} == {
        "gft",
        "plastic",
        "papier",
        "restafval",
        "reiniging",
        "pickup_today",
        "pickup_tomorrow",
    }


async def test_garbage_sensor_values(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Pickup dates use the today/tomorrow/default formats."""
    await _setup(hass, mock_config_entry, aioclient_mock)

    gft = _state(hass, mock_config_entry, "gft")
    assert gft.state == pickup(0).strftime("Today %d-%m-%Y")
    assert gft.attributes["days_until_pickup"] == 0

    plastic = _state(hass, mock_config_entry, "plastic")
    assert plastic.state == pickup(1).strftime("Tomorrow %d-%m-%Y")
    assert plastic.attributes["days_until_pickup"] == 1

    papier = _state(hass, mock_config_entry, "papier")
    assert papier.state == pickup(5).strftime("%d-%m-%Y")
    assert papier.attributes["days_until_pickup"] == 5

    # Entries without a valid date are skipped
    for key in ("restafval", "reiniging"):
        state = _state(hass, mock_config_entry, key)
        assert state.state == STATE_UNKNOWN
        assert "days_until_pickup" not in state.attributes


async def test_aggregate_sensor_values(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Today/tomorrow sensors list the bins being collected."""
    await _setup(hass, mock_config_entry, aioclient_mock)

    today = _state(hass, mock_config_entry, "pickup_today")
    assert today.state == "Green bin"
    assert today.attributes["garbage_types"] == ["gft"]
    assert today.attributes["count"] == 1

    tomorrow = _state(hass, mock_config_entry, "pickup_tomorrow")
    assert tomorrow.state == "Plastic"
    assert tomorrow.attributes["garbage_types"] == ["plastic"]


async def test_aggregate_sensor_nothing_scheduled(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Without pickups today the aggregate sensor reports None."""
    schedule = [
        {"id": 5, "ophaaldatum": pickup(1).isoformat()},
        {"id": 3, "ophaaldatum": pickup(1).isoformat()},
    ]
    await _setup(hass, mock_config_entry, aioclient_mock, schedule=schedule)

    today = _state(hass, mock_config_entry, "pickup_today")
    assert today.state == "None"
    assert today.attributes["count"] == 0
    assert _state(hass, mock_config_entry, "pickup_tomorrow").state == "Green bin + Blue bin"


@pytest.mark.parametrize(
    ("language", "fmt", "expected"),
    [
        ("nl", "%A %d %B", ("Maandag", "januari")),
        ("de", "%a %b", ("Mo", "Jan")),
        ("fr", "%A %B", ("Lundi", "janvier")),
        ("en", "%a %d %b", ("Mon", "Jan")),
    ],
)
async def test_localized_date_format(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    language: str,
    fmt: str,
    expected: tuple[str, str],
) -> None:
    """Day and month names follow the Home Assistant language."""
    hass.config.language = language
    entry = MockConfigEntry(
        domain="hvcgroep",
        data={"postal_code": "1234AB", "house_number": "1"},
        options={
            CONF_DATE_FORMAT_DEFAULT: fmt,
            CONF_DATE_FORMAT_TODAY: fmt,
            CONF_DATE_FORMAT_TOMORROW: fmt,
        },
    )
    # 2124-01-03 is a Monday in January
    await _setup(
        hass,
        entry,
        aioclient_mock,
        schedule=[{"id": 3, "ophaaldatum": "2124-01-03"}],
    )

    state = _state(hass, entry, "papier").state
    for part in expected:
        assert part in state


async def test_aggregate_sensor_dutch(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Non-English installs get Dutch bin names."""
    hass.config.language = "nl"
    await _setup(hass, mock_config_entry, aioclient_mock)

    assert _state(hass, mock_config_entry, "pickup_today").state == "Groene bak"
