"""Constants for the Maico REC DUO WiFi integration."""

from enum import IntEnum

DOMAIN = "maico"

# Cognito / AWS defaults (public endpoints, no secrets)
DEFAULT_COGNITO_POOL_URL = "https://eu-west-1xk36vsfYu.auth.eu-west-1"
DEFAULT_COGNITO_CLIENT_ID = "2dr9n1qsf4a5oitgup411vgtl8"
DEFAULT_COGNITO_CLOUD_URL = "https://bo3ezqpgv3.execute-api.eu-west-1.amazonaws.com/Prod"
DEFAULT_COGNITO_WSS_URL = "wss://xvo36hrhng.execute-api.eu-west-1.amazonaws.com/production/"
COGNITO_REDIRECT_URI = "myrecvmc://login"

# Config entry keys for Cognito settings
CONF_COGNITO_CLIENT_ID = "cognito_client_id"
CONF_COGNITO_CLIENT_SECRET = "cognito_client_secret"
CONF_COGNITO_POOL_URL = "cognito_pool_url"
CONF_COGNITO_CLOUD_URL = "cognito_cloud_url"
CONF_COGNITO_WSS_URL = "cognito_wss_url"

# Config entry keys
CONF_ACCESS_TOKEN = "access_token"
CONF_ID_TOKEN = "id_token"
CONF_REFRESH_TOKEN = "refresh_token"

# Timing
DEFAULT_SCAN_INTERVAL = 60  # seconds
ONLINE_THRESHOLD = 120  # seconds — device is offline if last update > this

# Local commands (per-device, use lccmd + sdst = device MAC)
CMD_POWER_OFF = 0x01
CMD_POWER_ON = 0x02
CMD_BOOST_ON = 0x03
CMD_BOOST_OFF = 0x04
CMD_SLEEP_ON = 0x05
CMD_SLEEP_OFF = 0x06
CMD_CLEAN_FILTER = 0x17
CMD_REBOOT = 0x20
CMD_FACTORY_RESET = 0x2C
CMD_SET_AQS_THRESHOLD = 0x31
CMD_SET_HUM_THRESHOLD = 0x32
CMD_SET_LED_BRIGHTNESS = 0x33
CMD_SET_DEVICE_ALIAS = 0x3F

# Global commands (ambient-wide, use glcmd + sdst = "ffffffffffff")
CMD_PUSH_PULL = 0x40
CMD_FLOW_EXTRACT = 0x41
CMD_FLOW_SUPPLY = 0x42
CMD_FREE_COOL1 = 0x43
CMD_FREE_COOL2 = 0x44
CMD_SET_SPEED_LOW = 0x61
CMD_SET_SPEED_RUN = 0x62

BROADCAST_MAC = "ffffffffffff"


class DeviceMode(IntEnum):
    """Device operating modes (index matches API 'mode' field)."""

    IDLE = 0
    POWER_OFF = 1
    PUSH_PULL = 2
    SLEEP = 3
    FLOW_CONTROL_EXTRACT = 4
    FLOW_CONTROL_SUPPLY = 5
    FREE_COOL_1 = 6
    FREE_COOL_2 = 7
    BOOST = 8
    LINE_BOOST = 9
    PULL_COORD_BOOST = 10
    HYGRO = 11
    AQS = 12
    PROVISIONING = 13
    FIRMWARE_UPGRADE = 14
    DEVICE_LOCKED = 15
    REBOOT_DEVICE = 16


# User-selectable ambient modes (shown in the mode selector)
SELECTABLE_MODES = {
    "Push/Pull": (DeviceMode.PUSH_PULL, CMD_PUSH_PULL),
    "Sola estrazione": (DeviceMode.FLOW_CONTROL_EXTRACT, CMD_FLOW_EXTRACT),
    "Sola immissione": (DeviceMode.FLOW_CONTROL_SUPPLY, CMD_FLOW_SUPPLY),
    "Raffrescamento": (DeviceMode.FREE_COOL_1, CMD_FREE_COOL1),
}

DEVICE_MODE_NAMES = {
    DeviceMode.IDLE: "Inattivo",
    DeviceMode.POWER_OFF: "Spento",
    DeviceMode.PUSH_PULL: "Push/Pull",
    DeviceMode.SLEEP: "Modalità notte",
    DeviceMode.FLOW_CONTROL_EXTRACT: "Sola estrazione",
    DeviceMode.FLOW_CONTROL_SUPPLY: "Sola immissione",
    DeviceMode.FREE_COOL_1: "Raffrescamento",
    DeviceMode.FREE_COOL_2: "Raffrescamento 2",
    DeviceMode.BOOST: "Boost",
    DeviceMode.LINE_BOOST: "Line Boost",
    DeviceMode.PULL_COORD_BOOST: "Pull Coord Boost",
    DeviceMode.HYGRO: "Igrostato",
    DeviceMode.AQS: "Qualità aria",
    DeviceMode.PROVISIONING: "Configurazione",
    DeviceMode.FIRMWARE_UPGRADE: "Aggiornamento firmware",
    DeviceMode.DEVICE_LOCKED: "Dispositivo bloccato",
    DeviceMode.REBOOT_DEVICE: "Riavvio in corso",
}

PLATFORMS = [
    "fan",
    "sensor",
    "binary_sensor",
    "select",
    "number",
    "switch",
    "button",
]

# Default durations for boost/sleep (minutes)
DEFAULT_BOOST_DURATION = 30
DEFAULT_SLEEP_DURATION = 30
