"""Shared device so all entities show up under one "easyVerein" service."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import EasyVereinConfigEntry


def device_info(entry: EasyVereinConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="easyVerein",
        name="easyVerein",
    )
