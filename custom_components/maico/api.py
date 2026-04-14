"""API client for Maico REC DUO WiFi cloud backend."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime

import aiohttp

from .const import BROADCAST_MAC, COGNITO_REDIRECT_URI
from .models import MaicoAmbient, MaicoDevice

_LOGGER = logging.getLogger(__name__)

# WebSocket reconnect backoff
WS_BACKOFF_STEPS = [1, 2, 4, 8, 10]


class MaicoApiError(Exception):
    """Raised on API errors."""


class MaicoAuthError(MaicoApiError):
    """Raised on authentication errors."""


class MaicoApiClient:
    """Client for the Maico cloud API."""

    def __init__(
        self,
        pool_url: str,
        client_id: str,
        client_secret: str,
        cloud_url: str,
        wss_url: str,
    ) -> None:
        self._pool_url = pool_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._cloud_url = cloud_url
        self._wss_url = wss_url
        self._token_url = f"{pool_url}.amazoncognito.com/oauth2/token"
        self._access_token: str | None = None
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0
        self._session: aiohttp.ClientSession | None = None
        self._command_lock = asyncio.Lock()
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ws_task: asyncio.Task | None = None
        self._ws_running = False
        self._on_token_refresh: callable | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the API client."""
        self._ws_running = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Authentication ──────────────────────────────────────────────

    async def authenticate_with_password(self, username: str, password: str) -> dict:
        """Authenticate via the Cognito hosted UI form (server-side POST)."""
        import re
        import urllib.parse

        session = await self._get_session()
        login_url = (
            f"{self._pool_url}.amazoncognito.com/login"
            f"?client_id={self._client_id}"
            f"&redirect_uri={urllib.parse.quote(COGNITO_REDIRECT_URI, safe='')}"
            f"&response_type=code&scope=email+openid+phone&lang=it"
        )

        # Step 1: GET the login page to obtain CSRF token and cookies
        async with session.get(login_url, allow_redirects=True) as resp:
            if resp.status != 200:
                raise MaicoAuthError(f"Failed to load login page (HTTP {resp.status})")
            html = await resp.text()

        csrf_match = re.search(r'name="csrf"\s+value="([^"]+)"', html)
        if not csrf_match:
            raise MaicoAuthError("Could not find CSRF token on login page")
        csrf_token = csrf_match.group(1)

        # Step 2: POST credentials (don't follow the redirect to myrecvmc://)
        async with session.post(
            login_url,
            data={
                "csrf": csrf_token,
                "username": username,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        ) as resp:
            if resp.status == 302:
                location = resp.headers.get("Location", "")
                if "code=" in location:
                    # Extract auth code from redirect URL
                    parsed = urllib.parse.urlparse(location)
                    params = urllib.parse.parse_qs(parsed.query)
                    auth_code = params.get("code", [None])[0]
                    if auth_code:
                        return await self.authenticate(auth_code)
                raise MaicoAuthError("Redirect did not contain auth code")
            elif resp.status == 400:
                raise MaicoAuthError("Invalid username or password")
            else:
                raise MaicoAuthError(f"Login failed (HTTP {resp.status})")

    async def authenticate(self, auth_code: str) -> dict:
        """Exchange an authorization code for tokens."""
        session = await self._get_session()
        async with session.post(
            self._token_url,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": COGNITO_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise MaicoAuthError(
                    f"Authentication failed (HTTP {resp.status}): {body}"
                )
            data = await resp.json()

        self._access_token = data["access_token"]
        self._id_token = data["id_token"]
        self._refresh_token = data["refresh_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60

        return {
            "access_token": self._access_token,
            "id_token": self._id_token,
            "refresh_token": self._refresh_token,
        }

    async def restore_session(
        self,
        access_token: str | None,
        id_token: str | None,
        refresh_token: str | None,
    ) -> None:
        """Restore a session from stored tokens."""
        self._access_token = access_token
        self._id_token = id_token
        self._refresh_token = refresh_token
        # Force refresh on next request
        self._token_expiry = 0

    async def _ensure_valid_token(self) -> None:
        """Refresh the access token if expired."""
        if self._access_token and time.time() < self._token_expiry:
            return
        if not self._refresh_token:
            raise MaicoAuthError("No refresh token available")

        # Try Cognito IDP API first (works with USER_PASSWORD_AUTH flow)
        session = await self._get_session()
        try:
            # We need a username for SECRET_HASH but during refresh we may not have it.
            # Use the OAuth2 token endpoint which doesn't need SECRET_HASH per-user.
            async with session.post(
                self._token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status != 200:
                    raise MaicoAuthError("Token refresh failed")
                data = await resp.json()

            self._access_token = data["access_token"]
            self._id_token = data.get("id_token", self._id_token)
            self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
            _LOGGER.debug("Token refreshed, expires in %s seconds", data.get("expires_in", 3600))
            # Notify listener to persist tokens
            if self._on_token_refresh:
                self._on_token_refresh()
        except Exception as err:
            raise MaicoAuthError(f"Token refresh failed: {err}") from err

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    def get_tokens(self) -> dict[str, str | None]:
        """Return current tokens for persistence."""
        return {
            "access_token": self._access_token,
            "id_token": self._id_token,
            "refresh_token": self._refresh_token,
        }

    # ── REST API ────────────────────────────────────────────────────

    async def get_ambients(self) -> list[str]:
        """Get list of ambient IDs for the authenticated user."""
        await self._ensure_valid_token()
        session = await self._get_session()
        url = f"{self._cloud_url}/api/user/things"
        async with session.get(url, headers=self._auth_headers()) as resp:
            if resp.status == 404:
                return []
            if resp.status != 200:
                raise MaicoApiError(f"Failed to get ambients (HTTP {resp.status})")
            return await resp.json()

    async def get_ambient_shadow(self, ambient_id: str) -> dict:
        """Get the full shadow (state) for an ambient."""
        await self._ensure_valid_token()
        session = await self._get_session()
        url = f"{self._cloud_url}/api/user/things/{ambient_id}"
        async with session.get(url, headers=self._auth_headers()) as resp:
            if resp.status != 200:
                raise MaicoApiError(
                    f"Failed to get shadow for {ambient_id} (HTTP {resp.status})"
                )
            return await resp.json()

    async def send_local_command(
        self,
        ambient_id: str,
        device_mac: str,
        cmd: int,
        nval: int | None = None,
        sval: str | None = None,
    ) -> bool:
        """Send a local command to a specific device."""
        json_cmd: dict = {"lccmd": cmd, "sdst": device_mac}
        if nval is not None:
            json_cmd["nval"] = nval
        if sval is not None:
            json_cmd["sval"] = sval
        return await self._send_command(ambient_id, json_cmd)

    async def send_global_command(
        self,
        ambient_id: str,
        cmd: int,
        nval: int | None = None,
    ) -> bool:
        """Send a global command to all devices in an ambient."""
        json_cmd: dict = {"glcmd": cmd, "sdst": BROADCAST_MAC}
        if nval is not None:
            json_cmd["nval"] = nval
        return await self._send_command(ambient_id, json_cmd)

    async def _send_command(self, ambient_id: str, json_cmd: dict) -> bool:
        """Send a command, serialized through a lock."""
        async with self._command_lock:
            await self._ensure_valid_token()
            session = await self._get_session()
            url = f"{self._cloud_url}/api/user/things/{ambient_id}"
            async with session.post(
                url,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/json",
                },
                json=json_cmd,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "Command failed (HTTP %s): %s", resp.status, json_cmd
                    )
                return resp.status == 200

    # ── Shadow Parsing ──────────────────────────────────────────────

    @staticmethod
    def parse_ambient_shadow(
        ambient_id: str, shadow: dict
    ) -> MaicoAmbient:
        """Parse an ambient shadow JSON into model objects."""
        ambient = MaicoAmbient(
            ambient_id=ambient_id,
            name=shadow.get("alias", ambient_id),
            run_speed=shadow.get("idxrun", 0),
            low_speed=shadow.get("idxlow", 0),
        )

        for key, value in shadow.items():
            if not isinstance(value, dict):
                continue
            # Device keys are 12-char hex MAC addresses
            if len(key.strip()) != 12:
                continue

            tod = (value.get("tod", 0) & 0xFF) if isinstance(value.get("tod"), int) else 0
            device_type = "recDuo100WiFi" if tod == 1 else "recDuo150WiFi"

            device = MaicoDevice(
                device_id=key,
                name=value.get("alias", key),
                device_type=device_type,
                ambient_id=ambient_id,
                ambient_name=ambient.name,
            )

            # Parse state fields
            if "epoch" in value:
                device.last_update = datetime.fromtimestamp(value["epoch"])
            if "temp" in value:
                temp = value["temp"] / 10
                if -40 <= temp <= 80:  # filter startup sentinel (888.8)
                    device.air_temperature = temp
            if "hy" in value:
                hum = value["hy"] / 10
                if 0 <= hum <= 100:  # filter startup sentinel (888.8)
                    device.humidity = hum
            if "aqs" in value:
                aqs = value["aqs"] / 10
                if 0 <= aqs <= 500:  # filter startup sentinel
                    device.air_quality = aqs
            if "rpm" in value:
                rpm = value["rpm"]
                if 0 <= rpm <= 50000:  # filter startup sentinel
                    device.air_flow = rpm
            if "mode" in value:
                device.mode = max(0, min(16, value["mode"]))
            if "cnt_flt" in value:
                device.filter_working_time = value["cnt_flt"]
            if "thr_flt" in value:
                device.filter_cleaning_threshold = value["thr_flt"]
            if "boost_tm" in value:
                device.boost_time = value["boost_tm"]
            if "sleep_tm" in value:
                device.sleep_time = value["sleep_tm"]
            if "sys_flags" in value:
                device.is_master = bool(value["sys_flags"] & 0x80)
            if "sys_error" in value:
                device.system_error = value["sys_error"]
            if "fw_ver" in value:
                device.firmware_version = value["fw_ver"]

            # Parse settings
            if "brt_level" in value:
                device.led_brightness = (value["brt_level"] // 63) + 1
            if "hy_thr" in value:
                device.humidity_threshold = value["hy_thr"] // 10
            if "aqs_thr" in value:
                device.air_quality_threshold_active = value["aqs_thr"] != 5000

            ambient.devices[key] = device

        return ambient

    # ── WebSocket ───────────────────────────────────────────────────

    async def connect_websocket(
        self,
        ambient_ids: list[str],
        on_update: callable,
        on_connected: callable | None = None,
        on_disconnected: callable | None = None,
    ) -> None:
        """Start a WebSocket connection for real-time updates."""
        self._ws_running = True
        self._ws_task = asyncio.ensure_future(
            self._ws_loop(ambient_ids, on_update, on_connected, on_disconnected)
        )

    async def _ws_loop(
        self,
        ambient_ids: list[str],
        on_update: callable,
        on_connected: callable | None,
        on_disconnected: callable | None,
    ) -> None:
        """WebSocket connection loop with auto-reconnect."""
        backoff_idx = 0

        while self._ws_running:
            try:
                await self._ensure_valid_token()
                session = await self._get_session()
                # heartbeat=30: aiohttp sends a ping every 30s; if no pong is
                # received the connection is closed with an error, breaking out
                # of the read loop so the reconnect/backoff path runs. Without
                # this, the `async for msg in self._ws` below can block
                # indefinitely on a half-dead connection (AWS IoT sometimes
                # stops delivering shadow updates without closing the socket,
                # e.g. when the auth context expires server-side). The
                # token-expiry check inside the read loop only fires when a
                # message arrives, so without a heartbeat a silent server
                # means no reconnect ever happens.
                self._ws = await session.ws_connect(
                    self._wss_url, heartbeat=30
                )
                backoff_idx = 0  # reset on successful connect

                # Subscribe to all ambients
                for ambient_id in ambient_ids:
                    msg = json.dumps(
                        {"action": "subscribe", "message": ambient_id}
                    )
                    await self._ws.send_str(msg)

                _LOGGER.debug("WebSocket connected, subscribed to %d ambients", len(ambient_ids))
                if on_connected:
                    on_connected()

                # Read messages, but reconnect before token expires
                async for msg in self._ws:
                    # Proactively close WS if token is about to expire (2 min buffer)
                    if time.time() > self._token_expiry - 120:
                        _LOGGER.debug("Token expiring soon, forcing refresh and reconnecting WebSocket")
                        self._token_expiry = 0  # force refresh on reconnect
                        await self._ws.close()
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            if "ThingName" in data and "Data" in data:
                                shadow = json.loads(data["Data"])
                                ambient = self.parse_ambient_shadow(
                                    data["ThingName"], shadow
                                )
                                await on_update(ambient, shadow)
                        except (json.JSONDecodeError, KeyError):
                            _LOGGER.debug("Ignoring malformed WS message")
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        break

            except asyncio.CancelledError:
                if on_disconnected:
                    on_disconnected()
                break
            except Exception:
                _LOGGER.debug("WebSocket disconnected, reconnecting...", exc_info=True)

            if on_disconnected:
                on_disconnected()

            if not self._ws_running:
                break

            # Exponential backoff
            delay = WS_BACKOFF_STEPS[min(backoff_idx, len(WS_BACKOFF_STEPS) - 1)]
            backoff_idx += 1
            await asyncio.sleep(delay)

    def disconnect_websocket(self) -> None:
        """Stop the WebSocket connection."""
        self._ws_running = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
