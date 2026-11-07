"""Tests for HVC Groep setup and unload."""

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.hvcgroep.const import CONF_DATE_FORMAT_DEFAULT, DOMAIN

from .conftest import BAGID_API, ENTRY_DATA, WASTE_API, mock_api


async def test_setup_and_unload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The entry sets up, stores its coordinator and unloads cleanly."""
    mock_api(aioclient_mock)
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.parametrize(
    ("bag_kwargs", "waste_kwargs"),
    [
        ({"json": []}, {"json": []}),
        ({"exc": aiohttp.ClientError()}, {"json": []}),
        ({"exc": TimeoutError()}, {"json": []}),
        ({"json": [{"bagId": "0123456789"}]}, {"exc": aiohttp.ClientError()}),
        ({"json": [{"bagId": "0123456789"}]}, {"exc": TimeoutError()}),
    ],
)
async def test_setup_retry_on_api_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    bag_kwargs: dict,
    waste_kwargs: dict,
) -> None:
    """A failing first refresh puts the entry in setup retry."""
    aioclient_mock.get(BAGID_API, **bag_kwargs)
    aioclient_mock.get(WASTE_API, **waste_kwargs)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_options_update_reloads_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Changing the options reloads the entry with the new date format."""
    mock_api(aioclient_mock)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    calls = aioclient_mock.call_count

    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_DATE_FORMAT_DEFAULT: "%Y/%m/%d"}
    )
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    # The reload creates a new coordinator that fetches the BAG ID and schedule again
    assert aioclient_mock.call_count == calls + 2


async def test_yaml_import(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A legacy sensor platform in configuration.yaml is imported."""
    mock_api(aioclient_mock)

    assert await async_setup_component(
        hass,
        DOMAIN,
        {"sensor": [{"platform": DOMAIN, "postcode": "1234 AB", "huisnummer": "1"}]},
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data == ENTRY_DATA


async def test_migrate_entry_is_noop(hass: HomeAssistant) -> None:
    """Migration of a version 1 entry succeeds without changes."""
    from custom_components.hvcgroep import async_migrate_entry

    entry = MockConfigEntry(domain=DOMAIN, data=dict(ENTRY_DATA), version=1)
    assert await async_migrate_entry(hass, entry) is True
    assert entry.data == ENTRY_DATA
