"""Data models for the Maico REC DUO WiFi integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .const import ONLINE_THRESHOLD


@dataclass
class MaicoDevice:
    """Represents a single REC DUO WiFi device."""

    device_id: str  # 12-char MAC address
    name: str
    device_type: str  # "recDuo100WiFi" or "recDuo150WiFi"
    ambient_id: str
    ambient_name: str

    # State
    mode: int | None = None
    air_temperature: float | None = None
    humidity: float | None = None
    air_quality: float | None = None
    air_flow: float | None = None
    filter_working_time: int | None = None
    filter_cleaning_threshold: int | None = None
    boost_time: int | None = None  # remaining seconds
    sleep_time: int | None = None  # remaining seconds
    is_master: bool | None = None
    system_error: int | None = None
    firmware_version: str | None = None
    last_update: datetime | None = None

    # Settings (None = not yet received from API)
    led_brightness: int | None = None
    humidity_threshold: int | None = None
    air_quality_threshold_active: bool | None = None

    @property
    def is_online(self) -> bool:
        """Device is online if last update was within threshold."""
        if self.last_update is None:
            return False
        delta = (datetime.now() - self.last_update).total_seconds()
        return delta < ONLINE_THRESHOLD

    @property
    def filter_needs_cleaning(self) -> bool:
        """Filter needs cleaning when working time exceeds threshold."""
        if self.filter_working_time is None or self.filter_cleaning_threshold is None:
            return False
        return self.filter_working_time >= self.filter_cleaning_threshold

    @property
    def model_name(self) -> str:
        """Human-readable model name."""
        if self.device_type == "recDuo100WiFi":
            return "REC DUO 100 WiFi"
        return "REC DUO 150 WiFi"


@dataclass
class MaicoAmbient:
    """Represents an ambient (zone/room) containing devices."""

    ambient_id: str
    name: str
    run_speed: int = 0  # 0-15
    low_speed: int = 0  # 0-15
    devices: dict[str, MaicoDevice] = field(default_factory=dict)
