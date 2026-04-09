"""Number platform for the Maico integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_SET_HUM_THRESHOLD,
    CMD_SET_LED_BRIGHTNESS,
    CMD_SET_SPEED_LOW,
    DEFAULT_BOOST_DURATION,
    DEFAULT_SLEEP_DURATION,
    DOMAIN,
)
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity

DURATIONS_KEY = f"{DOMAIN}_durations"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico number entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            aid = ambient.ambient_id
            did = device.device_id
            entities.extend([
                MaicoLedBrightnessNumber(coordinator, aid, did),
                MaicoHumidityThresholdNumber(coordinator, aid, did),
                MaicoLowSpeedNumber(coordinator, aid, did),
                MaicoBoostDurationNumber(coordinator, aid, did),
                MaicoSleepDurationNumber(coordinator, aid, did),
            ])

    async_add_entities(entities)


class MaicoLedBrightnessNumber(MaicoEntity, NumberEntity):
    """Number entity for LED brightness (1-5)."""

    _attr_translation_key = "led_brightness"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 5
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:led-on"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_led_brightness"

    @property
    def native_value(self) -> float | None:
        device = self._device
        if device is None:
            return None
        return device.led_brightness

    async def async_set_native_value(self, value: float) -> None:
        brightness = int(value)
        # Convert from 1-5 scale to 1-255 (matching Flutter: (val-1)*63+1)
        nval = (brightness - 1) * 63 + 1
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_LED_BRIGHTNESS, nval=nval
        )
        await self.coordinator.async_request_refresh()


class MaicoHumidityThresholdNumber(MaicoEntity, NumberEntity):
    """Number entity for humidity threshold (40-99%)."""

    _attr_translation_key = "humidity_threshold"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 40
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:water-percent"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_humidity_threshold"

    @property
    def native_value(self) -> float | None:
        device = self._device
        if device is None:
            return None
        return device.humidity_threshold

    async def async_set_native_value(self, value: float) -> None:
        # API expects threshold * 10
        nval = int(value) * 10
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_HUM_THRESHOLD, nval=nval
        )
        await self.coordinator.async_request_refresh()


class MaicoLowSpeedNumber(MaicoEntity, NumberEntity):
    """Number entity for night mode fan speed (displayed as 1-16, stored as 0-15)."""

    _attr_translation_key = "low_speed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 16
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:fan-chevron-down"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_low_speed"

    @property
    def native_value(self) -> float | None:
        ambient = self._ambient
        if ambient is None:
            return None
        # Display as 1-16 (API stores 0-15)
        return ambient.low_speed + 1

    async def async_set_native_value(self, value: float) -> None:
        # Convert from display 1-16 back to API 0-15
        await self.coordinator.api.send_global_command(
            self._ambient_id, CMD_SET_SPEED_LOW, nval=int(value) - 1
        )
        await self.coordinator.async_request_refresh()


class MaicoBoostDurationNumber(MaicoEntity, NumberEntity):
    """Number entity for boost duration (minutes)."""

    _attr_translation_key = "boost_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_boost_duration"

    @property
    def native_value(self) -> float:
        durations = self.hass.data.get(DURATIONS_KEY, {})
        return durations.get(f"{self._device_id}_boost", DEFAULT_BOOST_DURATION)

    async def async_set_native_value(self, value: float) -> None:
        self.hass.data.setdefault(DURATIONS_KEY, {})[f"{self._device_id}_boost"] = int(value)
        self.async_write_ha_state()


class MaicoSleepDurationNumber(MaicoEntity, NumberEntity):
    """Number entity for sleep/night mode duration (minutes)."""

    _attr_translation_key = "sleep_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_sleep_duration"

    @property
    def native_value(self) -> float:
        durations = self.hass.data.get(DURATIONS_KEY, {})
        return durations.get(f"{self._device_id}_sleep", DEFAULT_SLEEP_DURATION)

    async def async_set_native_value(self, value: float) -> None:
        self.hass.data.setdefault(DURATIONS_KEY, {})[f"{self._device_id}_sleep"] = int(value)
        self.async_write_ha_state()
