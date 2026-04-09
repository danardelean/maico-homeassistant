"""Config flow for Maico REC DUO WiFi integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .api import MaicoApiClient, MaicoAuthError
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
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Required("client_secret"): str,
    }
)


class MaicoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maico REC DUO WiFi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the user step — collect credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]
            client_secret = user_input["client_secret"].strip()

            api = MaicoApiClient(
                pool_url=DEFAULT_COGNITO_POOL_URL,
                client_id=DEFAULT_COGNITO_CLIENT_ID,
                client_secret=client_secret,
                cloud_url=DEFAULT_COGNITO_CLOUD_URL,
                wss_url=DEFAULT_COGNITO_WSS_URL,
            )
            try:
                tokens = await api.authenticate_with_password(username, password)
                await api.get_ambients()

                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Maico REC DUO ({username})",
                    data={
                        CONF_ACCESS_TOKEN: tokens["access_token"],
                        CONF_ID_TOKEN: tokens["id_token"],
                        CONF_REFRESH_TOKEN: tokens["refresh_token"],
                        CONF_COGNITO_CLIENT_ID: DEFAULT_COGNITO_CLIENT_ID,
                        CONF_COGNITO_CLIENT_SECRET: client_secret,
                        CONF_COGNITO_POOL_URL: DEFAULT_COGNITO_POOL_URL,
                        CONF_COGNITO_CLOUD_URL: DEFAULT_COGNITO_CLOUD_URL,
                        CONF_COGNITO_WSS_URL: DEFAULT_COGNITO_WSS_URL,
                    },
                )
            except MaicoAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
