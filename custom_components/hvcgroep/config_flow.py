"""Config flow for HVC Groep integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_HOUSE_NUMBER, CONF_POSTAL_CODE, DOMAIN
from .coordinator import validate_connection

_LOGGER = logging.getLogger(__name__)


class HVCGroepConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HVC Groep."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            postal_code = user_input[CONF_POSTAL_CODE].strip().upper().replace(" ", "")
            house_number = user_input[CONF_HOUSE_NUMBER].strip()

            # Create unique ID from postal code and house number
            await self.async_set_unique_id(f"{postal_code}_{house_number}")
            self._abort_if_unique_id_configured()

            # Validate connection
            if await validate_connection(self.hass, postal_code, house_number):
                return self.async_create_entry(
                    title=f"HVC Groep ({postal_code})",
                    data={
                        CONF_POSTAL_CODE: postal_code,
                        CONF_HOUSE_NUMBER: house_number,
                    },
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POSTAL_CODE): str,
                    vol.Required(CONF_HOUSE_NUMBER): str,
                }
            ),
            errors=errors,
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        postal_code = import_data.get(CONF_POSTAL_CODE, "").strip().upper().replace(" ", "")
        house_number = import_data.get(CONF_HOUSE_NUMBER, "").strip()

        if not postal_code or not house_number:
            _LOGGER.error("Missing postal_code or house_number in YAML import")
            return self.async_abort(reason="invalid_config")

        # Create unique ID from postal code and house number
        await self.async_set_unique_id(f"{postal_code}_{house_number}")
        self._abort_if_unique_id_configured()

        # Validate connection
        if not await validate_connection(self.hass, postal_code, house_number):
            _LOGGER.error("Cannot connect to HVC Groep API during YAML import")
            return self.async_abort(reason="cannot_connect")

        _LOGGER.info(
            "Migrating HVC Groep YAML configuration for %s to config entry",
            postal_code,
        )

        return self.async_create_entry(
            title=f"HVC Groep ({postal_code})",
            data={
                CONF_POSTAL_CODE: postal_code,
                CONF_HOUSE_NUMBER: house_number,
            },
        )
