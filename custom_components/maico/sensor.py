"""Sensor platform for the Maico integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_MODE_NAMES, DOMAIN
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity
from .models import MaicoDevice


@dataclass(frozen=True, kw_only=True)
class MaicoSensorEntityDescription(SensorEntityDescription):
    """Describes a Maico sensor entity."""

    value_fn: Callable[[MaicoDevice], float | int | str | None]


SENSOR_DESCRIPTIONS: tuple[MaicoSensorEntityDescription, ...] = (
    MaicoSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.air_temperature,
    ),
    MaicoSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.humidity,
    ),
    MaicoSensorEntityDescription(
        key="air_quality",
        translation_key="air_quality",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.air_quality,
    ),
    MaicoSensorEntityDescription(
        key="air_flow",
        translation_key="air_flow",
        native_unit_of_measurement="RPM",
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:fan",
        value_fn=lambda d: d.air_flow,
    ),
    MaicoSensorEntityDescription(
        key="filter_hours",
        translation_key="filter_hours",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:air-filter",
        value_fn=lambda d: d.filter_working_time,
    ),
    MaicoSensorEntityDescription(
        key="filter_threshold",
        translation_key="filter_threshold",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:air-filter",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.filter_cleaning_threshold,
    ),
    MaicoSensorEntityDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value_fn=lambda d: d.firmware_version,
    ),
    MaicoSensorEntityDescription(
        key="system_error",
        translation_key="system_error",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.system_error,
    ),
    MaicoSensorEntityDescription(
        key="operating_mode",
        translation_key="current_mode",
        icon="mdi:cog",
        value_fn=lambda d: DEVICE_MODE_NAMES.get(d.mode, "Unknown") if d.mode is not None else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico sensor entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MaicoSensorEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            for desc in SENSOR_DESCRIPTIONS:
                entities.append(
                    MaicoSensorEntity(
                        coordinator, ambient.ambient_id, device.device_id, desc
                    )
                )

    async_add_entities(entities)


class MaicoSensorEntity(MaicoEntity, SensorEntity):
    """Represents a Maico sensor."""

    entity_description: MaicoSensorEntityDescription

    def __init__(
        self,
        coordinator: MaicoDataUpdateCoordinator,
        ambient_id: str,
        device_id: str,
        description: MaicoSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, ambient_id, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> float | int | str | None:
        device = self._device
        if device is None:
            return None
        return self.entity_description.value_fn(device)
