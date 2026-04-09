"""Button platform for the Maico integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_CLEAN_FILTER, CMD_REBOOT, DOMAIN
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico button entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            aid = ambient.ambient_id
            did = device.device_id
            entities.extend([
                MaicoClearFilterButton(coordinator, aid, did),
                MaicoRebootButton(coordinator, aid, did),
            ])

    async_add_entities(entities)


class MaicoClearFilterButton(MaicoEntity, ButtonEntity):
    """Button to reset the filter counter."""

    _attr_translation_key = "clear_filter"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_clear_filter"

    async def async_press(self) -> None:
        """Clear the filter counter."""
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_CLEAN_FILTER
        )
        await self.coordinator.async_request_refresh()


class MaicoRebootButton(MaicoEntity, ButtonEntity):
    """Button to reboot the device."""

    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_reboot"

    async def async_press(self) -> None:
        """Reboot the device."""
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_REBOOT
        )
        await self.coordinator.async_request_refresh()
