"""
Config flow for Tasmota MiElHVAC integration.
"""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_BASE_TOPIC,
    CONF_MODEL,
    DEFAULT_NAME,
    DEFAULT_DEVICE_ID,
    DEFAULT_MODEL,
)


class MiElHVACTasmotaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmota MiElHVAC."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle user initiated flow."""
        errors = {}

        if user_input is not None:
            # Check device_id uniqueness
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): str,
            vol.Optional(CONF_BASE_TOPIC, default=DEFAULT_DEVICE_ID): str,
            vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return MiElHVACTasmotaOptionsFlow(config_entry)


class MiElHVACTasmotaOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_NAME,
                    default=self.config_entry.data.get(CONF_NAME, DEFAULT_NAME)
                ): str,
                vol.Optional(
                    CONF_BASE_TOPIC,
                    default=self.config_entry.data.get(
                        CONF_BASE_TOPIC, 
                        self.config_entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)
                    )
                ): str,
                vol.Optional(
                    CONF_MODEL,
                    default=self.config_entry.data.get(CONF_MODEL, DEFAULT_MODEL)
                ): str,
            })
        )

