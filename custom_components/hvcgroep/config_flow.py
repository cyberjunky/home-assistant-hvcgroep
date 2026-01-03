"""Config flow for HVC Groep integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_DATE_FORMAT_DEFAULT,
    CONF_DATE_FORMAT_TODAY,
    CONF_DATE_FORMAT_TOMORROW,
    CONF_HOUSE_NUMBER,
    CONF_POSTAL_CODE,
    DEFAULT_DATE_FORMAT,
    DEFAULT_DATE_FORMAT_TODAY,
    DEFAULT_DATE_FORMAT_TOMORROW,
    DOMAIN,
)
from .coordinator import validate_connection

_LOGGER = logging.getLogger(__name__)


class HVCGroepConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HVC Groep."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return HVCGroepOptionsFlow()

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


class HVCGroepOptionsFlow(OptionsFlow):
    """Handle options flow for HVC Groep."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values or defaults
        options = self.config_entry.options
        current_default = options.get(CONF_DATE_FORMAT_DEFAULT, DEFAULT_DATE_FORMAT)
        current_today = options.get(CONF_DATE_FORMAT_TODAY, DEFAULT_DATE_FORMAT_TODAY)
        current_tomorrow = options.get(
            CONF_DATE_FORMAT_TOMORROW, DEFAULT_DATE_FORMAT_TOMORROW
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DATE_FORMAT_DEFAULT,
                        default=current_default,
                    ): str,
                    vol.Optional(
                        CONF_DATE_FORMAT_TODAY,
                        default=current_today,
                    ): str,
                    vol.Optional(
                        CONF_DATE_FORMAT_TOMORROW,
                        default=current_tomorrow,
                    ): str,
                }
            ),
        )
