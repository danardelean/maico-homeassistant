"""Binary sensor platform for the Maico integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity
from .models import MaicoDevice


@dataclass(frozen=True, kw_only=True)
class MaicoBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Maico binary sensor entity."""

    value_fn: Callable[[MaicoDevice], bool | None]
    availability_fn: Callable[[MaicoDevice], bool] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[MaicoBinarySensorEntityDescription, ...] = (
    MaicoBinarySensorEntityDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.is_online,
        # Online sensor is always available (even when device is offline)
        availability_fn=lambda d: True,
    ),
    MaicoBinarySensorEntityDescription(
        key="filter_warning",
        translation_key="filter_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
        value_fn=lambda d: d.filter_needs_cleaning,
    ),
    MaicoBinarySensorEntityDescription(
        key="is_master",
        translation_key="is_master",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:star",
        value_fn=lambda d: d.is_master,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico binary sensor entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MaicoBinarySensorEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            for desc in BINARY_SENSOR_DESCRIPTIONS:
                entities.append(
                    MaicoBinarySensorEntity(
                        coordinator, ambient.ambient_id, device.device_id, desc
                    )
                )

    async_add_entities(entities)


class MaicoBinarySensorEntity(MaicoEntity, BinarySensorEntity):
    """Represents a Maico binary sensor."""

    entity_description: MaicoBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MaicoDataUpdateCoordinator,
        ambient_id: str,
        device_id: str,
        description: MaicoBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, ambient_id, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def available(self) -> bool:
        device = self._device
        if device is None:
            return False
        if self.entity_description.availability_fn is not None:
            return self.entity_description.availability_fn(device)
        return device.is_online

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            return None
        return self.entity_description.value_fn(device)
