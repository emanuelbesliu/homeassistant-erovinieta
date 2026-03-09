"""Config flow for eRovinieta."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import ERovignetaAPI, ERovignetaAPIError
from .const import (
    DOMAIN,
    CONF_PLATE_NUMBER,
    CONF_VIN,
    CONF_UPDATE_INTERVAL,
    CONF_EXPIRY_WARNING_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_EXPIRY_WARNING_DAYS,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ERovignetaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for eRovinieta."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step (plate number + VIN)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            plate = user_input[CONF_PLATE_NUMBER].upper().strip()
            vin = user_input[CONF_VIN].upper().strip()

            # Check for duplicate
            await self.async_set_unique_id(plate)
            self._abort_if_unique_id_configured()

            # Validate by making a test API call
            try:
                api = ERovignetaAPI()
                await api.async_validate(plate, vin)
            except ERovignetaAPIError as err:
                _LOGGER.error("eRovinieta validation failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Unexpected error during validation: %s", err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Rovinieta {plate}",
                    data={
                        CONF_PLATE_NUMBER: plate,
                        CONF_VIN: vin,
                        CONF_UPDATE_INTERVAL: user_input.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                        CONF_EXPIRY_WARNING_DAYS: user_input.get(
                            CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS
                        ),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PLATE_NUMBER): str,
                vol.Required(CONF_VIN): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
                vol.Optional(
                    CONF_EXPIRY_WARNING_DAYS,
                    default=DEFAULT_EXPIRY_WARNING_DAYS,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=365),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return ERovignetaOptionsFlowHandler(config_entry)


class ERovignetaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle eRovinieta options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        current_warning_days = self.config_entry.options.get(
            CONF_EXPIRY_WARNING_DAYS,
            self.config_entry.data.get(
                CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS
            ),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
                vol.Optional(
                    CONF_EXPIRY_WARNING_DAYS,
                    default=current_warning_days,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1, max=365),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
