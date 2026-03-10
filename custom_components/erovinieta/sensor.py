"""Sensor entities for eRovinieta."""

import logging
from datetime import date, datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTRIBUTION, CONF_PLATE_NUMBER
from .coordinator import ERovignetaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CURRENCY_RON = "RON"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eRovinieta sensors from a config entry."""
    coordinator: ERovignetaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    plate = entry.data[CONF_PLATE_NUMBER]

    entities = [
        ERovignetaDaysRemainingSensor(coordinator, entry, plate),
        ERovignetaExpiryDateSensor(coordinator, entry, plate),
        ERovignetaPriceSensor(coordinator, entry, plate),
        ERovignetaOwnerSensor(coordinator, entry, plate),
    ]

    async_add_entities(entities)
    _LOGGER.info("Created %d eRovinieta sensors for %s", len(entities), plate)


class ERovignetaBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for eRovinieta."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize base sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._plate = plate

    @property
    def device_info(self) -> dict[str, Any]:
        """Device info — groups all sensors under one device per vehicle."""
        return {
            "identifiers": {(DOMAIN, self._plate)},
            "name": f"Rovinieta {self._plate}",
            "manufacturer": "CNAIR Romania",
            "model": "eRovinieta",
            "entry_type": "service",
        }


class ERovignetaDaysRemainingSensor(ERovignetaBaseSensor):
    """Sensor for days remaining until rovinieta expires."""

    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = "days"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize days remaining sensor."""
        super().__init__(coordinator, entry, plate)
        self._attr_name = f"Rovinieta {plate} Days Remaining"
        self._attr_unique_id = f"{DOMAIN}_{plate}_days_remaining"

    @property
    def native_value(self) -> int | None:
        """Return the number of days remaining."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("days_remaining", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""
        data = self.coordinator.data or {}
        return {
            "plate_number": self._plate,
            "status": data.get("status"),
            "series": data.get("series"),
            "vehicle_category": data.get("vehicle_category"),
            "duration": data.get("duration"),
            "start_date": data.get("start_date"),
            "last_update": data.get("last_update"),
        }


class ERovignetaExpiryDateSensor(ERovignetaBaseSensor):
    """Sensor for the rovinieta expiry date."""

    _attr_icon = "mdi:calendar-remove"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize expiry date sensor."""
        super().__init__(coordinator, entry, plate)
        self._attr_name = f"Rovinieta {plate} Expiry Date"
        self._attr_unique_id = f"{DOMAIN}_{plate}_expiry_date"

    @property
    def native_value(self) -> date | None:
        """Return the expiry date."""
        data = self.coordinator.data or {}
        expiry_str = data.get("expiry_date")
        if not expiry_str:
            return None
        try:
            return datetime.fromisoformat(expiry_str).date()
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""
        data = self.coordinator.data or {}
        return {
            "plate_number": self._plate,
            "valid": data.get("valid", False),
            "country": data.get("country"),
        }


class ERovignetaPriceSensor(ERovignetaBaseSensor):
    """Sensor for the rovinieta price paid."""

    _attr_icon = "mdi:cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_RON

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize price sensor."""
        super().__init__(coordinator, entry, plate)
        self._attr_name = f"Rovinieta {plate} Price"
        self._attr_unique_id = f"{DOMAIN}_{plate}_price"

    @property
    def native_value(self) -> float | None:
        """Return the price paid in RON."""
        data = self.coordinator.data or {}
        price = data.get("price")
        if price is None:
            return None
        try:
            return float(price)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""
        data = self.coordinator.data or {}
        return {
            "plate_number": self._plate,
            "duration": data.get("duration"),
            "vehicle_category": data.get("vehicle_category"),
        }


class ERovignetaOwnerSensor(ERovignetaBaseSensor):
    """Sensor for the rovinieta owner (payer) information."""

    _attr_icon = "mdi:account"

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize owner sensor."""
        super().__init__(coordinator, entry, plate)
        self._attr_name = f"Rovinieta {plate} Owner"
        self._attr_unique_id = f"{DOMAIN}_{plate}_owner"

    @property
    def native_value(self) -> str | None:
        """Return the owner name."""
        data = self.coordinator.data or {}
        return data.get("owner_name") or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""
        data = self.coordinator.data or {}
        return {
            "plate_number": self._plate,
            "email": data.get("owner_email"),
            "vin": data.get("vin"),
        }
