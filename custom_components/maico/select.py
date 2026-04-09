"""Select platform for the Maico integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SELECTABLE_MODES, DeviceMode
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity

# Reverse mapping: DeviceMode -> select option key
_MODE_TO_OPTION: dict[int, str] = {
    mode_enum.value: key for key, (mode_enum, _) in SELECTABLE_MODES.items()
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico select entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MaicoModeSelect] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            entities.append(
                MaicoModeSelect(coordinator, ambient.ambient_id, device.device_id)
            )

    async_add_entities(entities)


class MaicoModeSelect(MaicoEntity, SelectEntity):
    """Select entity for the ventilation operating mode."""

    _attr_translation_key = "operating_mode"
    _attr_options = list(SELECTABLE_MODES.keys())
    _attr_icon = "mdi:hvac"

    def __init__(
        self,
        coordinator: MaicoDataUpdateCoordinator,
        ambient_id: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_mode"

    @property
    def current_option(self) -> str | None:
        device = self._device
        if device is None or device.mode is None:
            return None
        return _MODE_TO_OPTION.get(device.mode)

    async def async_select_option(self, option: str) -> None:
        """Change the operating mode."""
        if option not in SELECTABLE_MODES:
            return
        _, cmd = SELECTABLE_MODES[option]
        await self.coordinator.api.send_global_command(self._ambient_id, cmd)
        await self.coordinator.async_request_refresh()
