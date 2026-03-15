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
        self.api = ERovignetaAPI()

        self.plate_number: str = entry.data[CONF_PLATE_NUMBER]
        self.vin: str = entry.data[CONF_VIN]

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
        try:
            raw = await self.api.async_get_roadtax(self.plate_number, self.vin)
        except ERovignetaConnectionError as err:
            raise UpdateFailed(
                f"Connection error to erovinieta.ro: {err}"
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
        """Parse raw API response into a clean data dict."""
        records = raw.get("data", [])

        if not records:
            return {
                "valid": False,
                "records": [],
                "active_record": None,
                "days_remaining": 0,
                "expiry_date": None,
                "last_update": datetime.now(timezone.utc).isoformat(),
            }

        # Find the active record (status.id == 4 means "Activa")
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        active_record = None

        for record in records:
            status_id = record.get("status", {}).get("id")
            data_stop = record.get("dataStop", 0)
            if status_id == 4 and data_stop > now_ms:
                # Pick the one with the latest expiry if multiple are active
                if active_record is None or data_stop > active_record.get("dataStop", 0):
                    active_record = record

        if active_record:
            expiry_dt = datetime.fromtimestamp(
                active_record["dataStop"] / 1000, tz=timezone.utc
            )
            start_dt = datetime.fromtimestamp(
                active_record["dataStart"] / 1000, tz=timezone.utc
            )
            days_remaining = max(
                0, (expiry_dt - datetime.now(timezone.utc)).days
            )

            # Extract payment/owner info from grup
            grup = active_record.get("grup", {})
            platitor = grup.get("platitor", {})

            return {
                "valid": True,
                "days_remaining": days_remaining,
                "expiry_date": expiry_dt.isoformat(),
                "start_date": start_dt.isoformat(),
                "status": active_record.get("status", {}).get("denumire", "Unknown"),
                "series": active_record.get("serie", ""),
                "vehicle_category": active_record.get("categorieVehicol", {}).get(
                    "descriere", ""
                ),
                "vehicle_category_code": active_record.get("categorieVehicol", {}).get(
                    "cod", ""
                ),
                "duration": active_record.get("durataValabilitate", {}).get(
                    "descriere", ""
                ),
                "country": active_record.get("tara", {}).get("denumire", ""),
                "price": grup.get("valoareTotalaCuTva"),
                "vignette_count": grup.get("numarVignette"),
                "owner_name": platitor.get("nume", ""),
                "owner_email": platitor.get("email", ""),
                "plate_number": active_record.get("nrAuto", self.plate_number),
                "vin": active_record.get("serieSasiu", self.vin),
                "records": records,
                "active_record": active_record,
                "last_update": datetime.now(timezone.utc).isoformat(),
            }

        # No active record — might be expired
        # Use the most recent record for historical info
        latest = max(records, key=lambda r: r.get("dataStop", 0))
        expiry_dt = datetime.fromtimestamp(
            latest["dataStop"] / 1000, tz=timezone.utc
        )
        start_dt = datetime.fromtimestamp(
            latest["dataStart"] / 1000, tz=timezone.utc
        )
        grup = latest.get("grup", {})
        platitor = grup.get("platitor", {})

        return {
            "valid": False,
            "days_remaining": 0,
            "expiry_date": expiry_dt.isoformat(),
            "start_date": start_dt.isoformat(),
            "status": latest.get("status", {}).get("denumire", "Unknown"),
            "series": latest.get("serie", ""),
            "vehicle_category": latest.get("categorieVehicol", {}).get(
                "descriere", ""
            ),
            "vehicle_category_code": latest.get("categorieVehicol", {}).get(
                "cod", ""
            ),
            "duration": latest.get("durataValabilitate", {}).get("descriere", ""),
            "country": latest.get("tara", {}).get("denumire", ""),
            "price": grup.get("valoareTotalaCuTva"),
            "vignette_count": grup.get("numarVignette"),
            "owner_name": platitor.get("nume", ""),
            "owner_email": platitor.get("email", ""),
            "plate_number": latest.get("nrAuto", self.plate_number),
            "vin": latest.get("serieSasiu", self.vin),
            "records": records,
            "active_record": None,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

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
