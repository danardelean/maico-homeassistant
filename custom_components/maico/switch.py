"""Switch platform for the Maico integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_BOOST_OFF,
    CMD_BOOST_ON,
    CMD_SET_AQS_THRESHOLD,
    CMD_SET_HUM_THRESHOLD,
    CMD_SLEEP_OFF,
    CMD_SLEEP_ON,
    DEFAULT_BOOST_DURATION,
    DEFAULT_SLEEP_DURATION,
    DOMAIN,
    DeviceMode,
)
from .coordinator import MaicoDataUpdateCoordinator
from .entity import MaicoEntity

DURATIONS_KEY = f"{DOMAIN}_durations"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maico switch entities."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for ambient in coordinator.data.values():
        for device in ambient.devices.values():
            aid = ambient.ambient_id
            did = device.device_id
            entities.extend([
                MaicoAQSSwitch(coordinator, aid, did),
                MaicoBoostSwitch(coordinator, aid, did),
                MaicoSleepSwitch(coordinator, aid, did),
            ])

    async_add_entities(entities)


class MaicoAQSSwitch(MaicoEntity, SwitchEntity):
    """Switch for air quality sensor threshold activation."""

    _attr_translation_key = "aqs_threshold"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:air-purifier"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_aqs_threshold"

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            return None
        if device.air_quality_threshold_active is None:
            return None
        return device.air_quality_threshold_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Active: nval = 101 * 10 = 1010
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_AQS_THRESHOLD, nval=1010
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Inactive: nval = 500 * 10 = 5000
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_AQS_THRESHOLD, nval=5000
        )
        await self.coordinator.async_request_refresh()


class MaicoHumidityThresholdSwitch(MaicoEntity, SwitchEntity):
    """Switch for humidity threshold activation."""

    _attr_translation_key = "humidity_threshold_active"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:water-percent-alert"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_humidity_threshold_active"

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            return None
        # Active when threshold < 100 (100 = disabled in the Flutter app)
        return device.humidity_threshold < 100

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Enable with default 80%: nval = 80 * 10 = 800
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_HUM_THRESHOLD, nval=800
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Disable: set to 100% which means off: nval = 100 * 10 = 1000
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SET_HUM_THRESHOLD, nval=1000
        )
        await self.coordinator.async_request_refresh()


class MaicoBoostSwitch(MaicoEntity, SwitchEntity):
    """Switch for timed boost mode."""

    _attr_translation_key = "boost_mode"
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_boost_mode"

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            return None
        return device.mode == DeviceMode.BOOST

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return remaining boost time."""
        device = self._device
        if device is None or device.boost_time is None:
            return {}
        return {"remaining_seconds": device.boost_time}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate boost mode with configured duration."""
        durations = self.hass.data.get(DURATIONS_KEY, {})
        duration_minutes = durations.get(f"{self._device_id}_boost", DEFAULT_BOOST_DURATION)
        await self.coordinator.api.send_local_command(
            self._ambient_id,
            self._device_id,
            CMD_BOOST_ON,
            nval=duration_minutes * 60,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate boost mode."""
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_BOOST_OFF
        )
        await self.coordinator.async_request_refresh()


class MaicoSleepSwitch(MaicoEntity, SwitchEntity):
    """Switch for timed sleep/night mode."""

    _attr_translation_key = "sleep_mode"
    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator, ambient_id, device_id):
        super().__init__(coordinator, ambient_id, device_id)
        self._attr_unique_id = f"{device_id}_sleep_mode"

    @property
    def is_on(self) -> bool | None:
        device = self._device
        if device is None:
            return None
        return device.mode == DeviceMode.SLEEP

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return remaining sleep time."""
        device = self._device
        if device is None or device.sleep_time is None:
            return {}
        return {"remaining_seconds": device.sleep_time}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate sleep mode with configured duration."""
        durations = self.hass.data.get(DURATIONS_KEY, {})
        duration_minutes = durations.get(f"{self._device_id}_sleep", DEFAULT_SLEEP_DURATION)
        await self.coordinator.api.send_local_command(
            self._ambient_id,
            self._device_id,
            CMD_SLEEP_ON,
            nval=duration_minutes * 60,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate sleep mode."""
        await self.coordinator.api.send_local_command(
            self._ambient_id, self._device_id, CMD_SLEEP_OFF
        )
        await self.coordinator.async_request_refresh()
