"""Base entity for the Maico integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MaicoDataUpdateCoordinator
from .models import MaicoAmbient, MaicoDevice


class MaicoEntity(CoordinatorEntity[MaicoDataUpdateCoordinator]):
    """Base class for Maico entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MaicoDataUpdateCoordinator,
        ambient_id: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._ambient_id = ambient_id
        self._device_id = device_id

    @property
    def _ambient(self) -> MaicoAmbient | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._ambient_id)

    @property
    def _device(self) -> MaicoDevice | None:
        ambient = self._ambient
        if ambient is None:
            return None
        return ambient.devices.get(self._device_id)

    @property
    def available(self) -> bool:
        device = self._device
        if device is None:
            return False
        return device.is_online

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.name if device else self._device_id,
            manufacturer="Maico",
            model=device.model_name if device else "REC DUO WiFi",
            sw_version=device.firmware_version if device else None,
            via_device=(DOMAIN, self._ambient_id),
        )
