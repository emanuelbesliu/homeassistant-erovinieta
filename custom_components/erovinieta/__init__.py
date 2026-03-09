"""eRovinieta integration for Home Assistant."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_EXPIRY_WARNING_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_EXPIRY_WARNING_DAYS,
)
from .coordinator import ERovignetaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up component from configuration.yaml (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eRovinieta from a config entry."""
    _LOGGER.debug("Setting up eRovinieta entry %s", entry.entry_id)

    coordinator = ERovignetaDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates so changes take effect without restart
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _LOGGER.debug("eRovinieta setup completed for %s", entry.entry_id)
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update — apply new interval and warning days live."""
    coordinator: ERovignetaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    new_interval = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )
    new_warning_days = entry.options.get(
        CONF_EXPIRY_WARNING_DAYS,
        entry.data.get(CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS),
    )

    coordinator.update_interval = timedelta(seconds=new_interval)
    coordinator.expiry_warning_days = new_warning_days

    _LOGGER.info(
        "eRovinieta options updated — interval: %ss, warning days: %d",
        new_interval,
        new_warning_days,
    )

    # Trigger immediate refresh with new settings
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an eRovinieta config entry."""
    _LOGGER.debug("Unloading eRovinieta entry %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
