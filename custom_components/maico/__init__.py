"""The Maico REC DUO WiFi integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import MaicoApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_COGNITO_CLIENT_ID,
    CONF_COGNITO_CLIENT_SECRET,
    CONF_COGNITO_CLOUD_URL,
    CONF_COGNITO_POOL_URL,
    CONF_COGNITO_WSS_URL,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DEFAULT_COGNITO_CLIENT_ID,
    DEFAULT_COGNITO_CLOUD_URL,
    DEFAULT_COGNITO_POOL_URL,
    DEFAULT_COGNITO_WSS_URL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MaicoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Maico REC DUO WiFi from a config entry."""
    api = MaicoApiClient(
        pool_url=entry.data.get(CONF_COGNITO_POOL_URL, DEFAULT_COGNITO_POOL_URL),
        client_id=entry.data.get(CONF_COGNITO_CLIENT_ID, DEFAULT_COGNITO_CLIENT_ID),
        client_secret=entry.data[CONF_COGNITO_CLIENT_SECRET],
        cloud_url=entry.data.get(CONF_COGNITO_CLOUD_URL, DEFAULT_COGNITO_CLOUD_URL),
        wss_url=entry.data.get(CONF_COGNITO_WSS_URL, DEFAULT_COGNITO_WSS_URL),
    )
    await api.restore_session(
        entry.data.get(CONF_ACCESS_TOKEN),
        entry.data.get(CONF_ID_TOKEN),
        entry.data.get(CONF_REFRESH_TOKEN),
    )

    coordinator = MaicoDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    # Store updated tokens back to config entry
    tokens = api.get_tokens()
    if tokens.get("refresh_token") != entry.data.get(CONF_REFRESH_TOKEN):
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **tokens},
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Maico config entry."""
    coordinator: MaicoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.shutdown_websocket()
    await coordinator.api.close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
