"""DataUpdateCoordinator for the Maico integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MaicoApiClient, MaicoApiError, MaicoAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import MaicoAmbient

_LOGGER = logging.getLogger(__name__)


class MaicoDataUpdateCoordinator(DataUpdateCoordinator[dict[str, MaicoAmbient]]):
    """Coordinator that polls the Maico cloud API and handles WebSocket updates.

    After the initial REST poll, a WebSocket connection is established for
    real-time updates. While the WebSocket is active, REST polling is disabled
    to minimize API traffic and AWS costs. If the WebSocket disconnects,
    polling resumes as a fallback until the WebSocket reconnects.
    """

    def __init__(self, hass: HomeAssistant, api: MaicoApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._ws_started = False

    async def _async_update_data(self) -> dict[str, MaicoAmbient]:
        """Fetch all ambients and their device states via REST."""
        try:
            ambient_ids = await self.api.get_ambients()
        except MaicoAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except MaicoApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        ambients: dict[str, MaicoAmbient] = {}

        for ambient_id in ambient_ids:
            try:
                shadow = await self.api.get_ambient_shadow(ambient_id)
                ambients[ambient_id] = MaicoApiClient.parse_ambient_shadow(
                    ambient_id, shadow
                )
            except MaicoApiError:
                _LOGGER.warning("Failed to fetch shadow for ambient %s", ambient_id)

        # Start WebSocket after first successful poll
        if not self._ws_started and ambients:
            self._ws_started = True
            await self.api.connect_websocket(
                list(ambients.keys()),
                self._handle_ws_update,
                self._on_ws_connected,
                self._on_ws_disconnected,
            )

        return ambients

    def _on_ws_connected(self) -> None:
        """Called when WebSocket connects — disable REST polling."""
        _LOGGER.debug("WebSocket connected, disabling REST polling")
        self.update_interval = None

    def _on_ws_disconnected(self) -> None:
        """Called when WebSocket disconnects — re-enable REST polling."""
        _LOGGER.debug("WebSocket disconnected, enabling REST polling fallback")
        self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    async def _handle_ws_update(self, ambient: MaicoAmbient, raw_shadow: dict) -> None:
        """Handle a real-time WebSocket update for an ambient."""
        if self.data is None:
            return

        # Merge the updated ambient into our data
        current = dict(self.data)
        if ambient.ambient_id in current:
            existing = current[ambient.ambient_id]
            # Only update ambient-level fields if present in the raw shadow
            if "alias" in raw_shadow:
                existing.name = ambient.name
            if "idxrun" in raw_shadow:
                existing.run_speed = ambient.run_speed
            if "idxlow" in raw_shadow:
                existing.low_speed = ambient.low_speed
            # Merge devices — only overwrite fields that have new values
            for device_id, new_device in ambient.devices.items():
                if device_id in existing.devices:
                    old = existing.devices[device_id]
                    for field in [
                        "name", "mode", "air_temperature", "humidity",
                        "air_quality", "air_flow", "filter_working_time",
                        "filter_cleaning_threshold", "boost_time", "sleep_time",
                        "is_master", "system_error", "firmware_version",
                        "last_update", "led_brightness", "humidity_threshold",
                        "air_quality_threshold_active",
                    ]:
                        new_val = getattr(new_device, field)
                        if new_val is not None:
                            setattr(old, field, new_val)
                else:
                    existing.devices[device_id] = new_device
            current[ambient.ambient_id] = existing
        else:
            current[ambient.ambient_id] = ambient

        self.async_set_updated_data(current)

    def shutdown_websocket(self) -> None:
        """Disconnect the WebSocket."""
        self._ws_started = False
        self.api.disconnect_websocket()
