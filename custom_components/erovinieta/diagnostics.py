"""Diagnostics support for eRovinieta."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN
from .coordinator import ERovignetaDataUpdateCoordinator

# Keys to redact from config entry data and coordinator data
REDACT_CONFIG = {
    "vin",
    "plate_number",
}

REDACT_COORDINATOR = {
    "vin",
    "plate_number",
    "owner_name",
    "owner_email",
    "nrAuto",
    "serieSasiu",
    "serie",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ERovignetaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redact sensitive data from coordinator
    coordinator_data = coordinator.data or {}
    redacted_data = async_redact_data(coordinator_data, REDACT_COORDINATOR)

    # Redact raw records and active_record nested dicts
    if "records" in redacted_data and isinstance(redacted_data["records"], list):
        redacted_data["records"] = [
            async_redact_data(r, REDACT_COORDINATOR)
            if isinstance(r, dict)
            else r
            for r in redacted_data["records"]
        ]
    if "active_record" in redacted_data and isinstance(
        redacted_data["active_record"], dict
    ):
        redacted_data["active_record"] = async_redact_data(
            redacted_data["active_record"], REDACT_COORDINATOR
        )

    return {
        "config_entry": {
            "data": async_redact_data(dict(entry.data), REDACT_CONFIG),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "expiry_warning_days": coordinator.expiry_warning_days,
            "data": redacted_data,
        },
    }
