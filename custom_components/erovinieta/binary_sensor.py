"""Binary sensor for eRovinieta — valid/expired status."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ATTRIBUTION, CONF_PLATE_NUMBER
from .coordinator import ERovignetaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eRovinieta binary sensor from a config entry."""
    coordinator: ERovignetaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    plate = entry.data[CONF_PLATE_NUMBER]

    async_add_entities([ERovignetaValidBinarySensor(coordinator, entry, plate)])


class ERovignetaValidBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor: ON when the vehicle has a valid rovinieta."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:highway"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
        self,
        coordinator: ERovignetaDataUpdateCoordinator,
        entry: ConfigEntry,
        plate: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._plate = plate
        self._attr_name = f"Rovinieta {plate} Valid"
        self._attr_unique_id = f"{DOMAIN}_{plate}_valid"

    @property
    def is_on(self) -> bool | None:
        """Return True if the vehicle has a valid (active) rovinieta."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("valid", False)

    @property
    def device_info(self) -> dict[str, Any]:
        """Device info — groups with other sensors for this vehicle."""
        return {
            "identifiers": {(DOMAIN, self._plate)},
            "name": f"Rovinieta {self._plate}",
            "manufacturer": "CNAIR Romania",
            "model": "eRovinieta",
            "entry_type": "service",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""
        data = self.coordinator.data or {}
        return {
            "plate_number": self._plate,
            "days_remaining": data.get("days_remaining", 0),
            "expiry_date": data.get("expiry_date"),
            "status": data.get("status"),
            "series": data.get("series"),
            "vehicle_category": data.get("vehicle_category"),
            "duration": data.get("duration"),
            "price": data.get("price"),
            "owner_name": data.get("owner_name"),
        }
