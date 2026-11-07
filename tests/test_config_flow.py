"""Tests for the HVC Groep config flow."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.hvcgroep.const import (
    CONF_DATE_FORMAT_DEFAULT,
    CONF_DATE_FORMAT_TODAY,
    CONF_DATE_FORMAT_TOMORROW,
    CONF_HOUSE_NUMBER,
    CONF_POSTAL_CODE,
    DOMAIN,
)

from .conftest import BAGID_API, ENTRY_DATA, mock_api


@pytest.fixture(autouse=True)
async def mock_setup_entry(hass: HomeAssistant) -> AsyncGenerator[AsyncMock]:
    """Prevent created entries from actually being set up."""
    with (
        patch("custom_components.hvcgroep.async_setup_entry", AsyncMock(return_value=True)) as mock,
        patch("custom_components.hvcgroep.async_unload_entry", AsyncMock(return_value=True)),
    ):
        yield mock
        # Unload while patched; the real unload expects state the mock never set up
        for entry in hass.config_entries.async_entries(DOMAIN):
            await hass.config_entries.async_unload(entry.entry_id)


async def test_user_flow_success(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A valid address creates an entry with a normalized postal code."""
    mock_api(aioclient_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_POSTAL_CODE: " 1234 ab ", CONF_HOUSE_NUMBER: " 1 "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HVC Groep (1234AB)"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == "1234AB_1"


@pytest.mark.parametrize(
    "mock_kwargs",
    [
        {"json": []},
        {"json": [{"bagId": None}]},
        {"exc": aiohttp.ClientError()},
        {"exc": TimeoutError()},
        {"status": 500},
    ],
)
async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_kwargs: dict
) -> None:
    """An unknown address or API failure shows an error and allows a retry."""
    aioclient_mock.get(BAGID_API, **mock_kwargs)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ENTRY_DATA)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ENTRY_DATA)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The same address cannot be added twice."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_POSTAL_CODE: "1234 ab", CONF_HOUSE_NUMBER: "1"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0


async def test_import_flow_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A legacy YAML configuration is imported as a config entry."""
    mock_api(aioclient_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_POSTAL_CODE: "1234ab", CONF_HOUSE_NUMBER: "1"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == ENTRY_DATA


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        ({CONF_POSTAL_CODE: "", CONF_HOUSE_NUMBER: "1"}, "invalid_config"),
        ({CONF_POSTAL_CODE: "1234AB"}, "invalid_config"),
        (ENTRY_DATA, "cannot_connect"),
    ],
)
async def test_import_flow_abort(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, data: dict, reason: str
) -> None:
    """An incomplete or unreachable YAML import aborts."""
    aioclient_mock.get(BAGID_API, json=[])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=data
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_import_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Importing an already configured address aborts."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(ENTRY_DATA)
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """The date formats can be changed through the options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    options = {
        CONF_DATE_FORMAT_DEFAULT: "%A %d %B",
        CONF_DATE_FORMAT_TODAY: "Vandaag",
        CONF_DATE_FORMAT_TOMORROW: "Morgen",
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], options)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == options
