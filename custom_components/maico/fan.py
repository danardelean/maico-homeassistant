"""Fan platform for the Maico integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import CMD_POWER_OFF, CMD_POWER_ON, CMD_SET_SPEED_RUN, DOMAIN, DeviceMode
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity

SPEED_RANGE = (0, 15)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico fan entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MaicoFanEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            entities.append(
                MaicoFanEntity(coordinator, ambient.ambient_id, device.device_id)
            )

    async_add_entities(entities)


class MaicoFanEntity(MaicoEntity, FanEntity):
    """Represents a Maico REC DUO ventilation fan."""

    _attr_translation_key = "ventilation"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 15

    def __init__(
        self,
        coordinator: MaicoDataUpdateCoordinator,
        ambient_id: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_fan"

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None or device.mode is None:
            return None
        return device.mode != DeviceMode.POWER_OFF

    @property
    def percentage(self) -> int | None:
        ambient = self._ambient
        if ambient is None:
            return None
        return ranged_value_to_percentage(SPEED_RANGE, ambient.run_speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        device = self._device
        if device is None:
            return
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_POWER_ON
        )
        if percentage is not None:
            await self.async_set_percentage(percentage)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_POWER_OFF
        )
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage."""
        speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.coordinator.api.send_global_command(
            self._ambient_id, CMD_SET_SPEED_RUN, nval=speed
        )
        await self.coordinator.async_request_refresh()
