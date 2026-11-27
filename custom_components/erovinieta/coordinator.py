"""Data Update Coordinator for eRovinieta.

Periodically queries the anonymous erovinieta.ro API (no account required)
to refresh vignette validity data for a single vehicle.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ERovignetaAPI
from .const import (
    DOMAIN,
    CONF_PLATE_NUMBER,
    CONF_VIN,
    CONF_SERIES,
    CONF_SOLVER_URL,
    DEFAULT_SOLVER_URL,
    CONF_UPDATE_INTERVAL,
    CONF_EXPIRY_WARNING_DAYS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_EXPIRY_WARNING_DAYS,
    EVENT_EXPIRING_SOON,
)
from .exceptions import ERovignetaAPIError, ERovignetaConnectionError

_LOGGER = logging.getLogger(__name__)


class ERovignetaDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching eRovinieta data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.plate_number: str = entry.data[CONF_PLATE_NUMBER]
        self.vin: str = entry.data[CONF_VIN]
        self.series: str = entry.options.get(
            CONF_SERIES, entry.data.get(CONF_SERIES, "")
        )
        solver_url: str = entry.options.get(
            CONF_SOLVER_URL, entry.data.get(CONF_SOLVER_URL, DEFAULT_SOLVER_URL)
        )
        self.api = ERovignetaAPI(solver_url)

        update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        self._expiry_warning_days: int = entry.options.get(
            CONF_EXPIRY_WARNING_DAYS,
            entry.data.get(CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS),
        )

        # Track whether we already fired the expiring-soon event this cycle
        self._last_event_fired_for: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.plate_number}",
            update_interval=timedelta(seconds=update_interval),
        )

    @property
    def expiry_warning_days(self) -> int:
        """Return the current expiry warning threshold."""
        return self._expiry_warning_days

    @expiry_warning_days.setter
    def expiry_warning_days(self, value: int) -> None:
        """Set a new expiry warning threshold."""
        self._expiry_warning_days = value

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the eRovinieta API."""
        if not self.series:
            raise UpdateFailed(
                "Registration certificate series is not configured. "
                "Open the integration's Configure dialog and set it."
            )
        try:
            raw = await self.api.async_get_roadtax(
                self.plate_number, self.vin, self.series
            )
        except ERovignetaConnectionError as err:
            raise UpdateFailed(
                f"Connection error to solver service: {err}"
            ) from err
        except ERovignetaAPIError as err:
            raise UpdateFailed(f"eRovinieta API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        # Parse the response into a clean structure
        parsed = self._parse_response(raw)

        # Fire expiry warning event if applicable
        self._check_expiry_warning(parsed)

        return parsed

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse the portal.etoll.ro vignette search response."""
        now = datetime.now(timezone.utc)
        records = (raw.get("data") or {}).get("content") or []
        base = {
            "valid": False,
            "days_remaining": 0,
            "expiry_date": None,
            "start_date": None,
            "status": None,
            "series": "",
            "vehicle_category": "",
            "emission_category": "",
            "price": None,
            "plate_number": self.plate_number,
            "vin": self.vin,
            "records": records,
            "active_record": None,
            "last_update": now.isoformat(),
        }
        if not records:
            return base

        def _dt(value: str | None) -> datetime:
            if not value:
                return datetime.min.replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        active = [
            r for r in records
            if _dt(r.get("validityStartDate")) <= now <= _dt(r.get("validityEndDate"))
        ]
        chosen = max(active or records, key=lambda r: _dt(r.get("validityEndDate")))
        expiry = _dt(chosen.get("validityEndDate"))
        base.update(
            {
                "valid": bool(active),
                "days_remaining": max(0, (expiry - now).days) if active else 0,
                "expiry_date": expiry.isoformat(),
                "start_date": _dt(chosen.get("validityStartDate")).isoformat(),
                "status": "Activa" if active else "Expirata",
                "series": chosen.get("series") or "",
                "vehicle_category": chosen.get("vehicleCategory") or "",
                "emission_category": chosen.get("emissionStandardsCategory") or "",
                "price": chosen.get("price"),
                "plate_number": chosen.get("licensePlateNumber", self.plate_number),
                "vin": chosen.get("vin", self.vin),
                "active_record": chosen if active else None,
            }
        )
        return base

    def _check_expiry_warning(self, data: dict[str, Any]) -> None:
        """Fire an event if the vignette is expiring within the warning threshold."""
        if not data.get("valid"):
            return

        days = data.get("days_remaining", 0)
        expiry_key = data.get("expiry_date", "")

        if days <= self._expiry_warning_days:
            # Only fire once per expiry date to avoid spamming
            if self._last_event_fired_for != expiry_key:
                self._last_event_fired_for = expiry_key
                self.hass.bus.async_fire(
                    EVENT_EXPIRING_SOON,
                    {
                        "plate_number": self.plate_number,
                        "days_remaining": days,
                        "expiry_date": expiry_key,
                    },
                )
                _LOGGER.info(
                    "Rovinieta for %s expiring in %d days (threshold: %d)",
                    self.plate_number,
                    days,
                    self._expiry_warning_days,
                )
