"""Count sensors (built-in counters, one per custom filter) and the next event."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import next_events
from .coordinator import EasyVereinConfigEntry, EasyVereinCoordinator
from .entity import device_info, sync_dynamic_entities

ICONS = {
    "members": "mdi:account-group",
    "applications": "mdi:account-clock",
    "resignations": "mdi:account-arrow-right",
    "new_members": "mdi:account-plus",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyVereinConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [NextEventSensor(coordinator)]
        + [CountSensor(coordinator, key) for key in coordinator.data.counts]
    )
    sync_dynamic_entities(
        hass,
        entry,
        coordinator,
        async_add_entities,
        domain="sensor",
        prefix="filter_",
        current_ids=lambda data: set(data.filter_counts),
        factory=lambda filter_id: FilterSensor(coordinator, filter_id),
    )


class _EasyVereinSensor(CoordinatorEntity[EasyVereinCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: EasyVereinCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = device_info(entry)


class CountSensor(_EasyVereinSensor):
    """Built-in counters on the member endpoint."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EasyVereinCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_translation_key = key
        self._attr_icon = ICONS[key]

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.counts.get(self._key)


class FilterSensor(_EasyVereinSensor):
    """Number of hits of one saved custom filter."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: EasyVereinCoordinator, filter_id: int) -> None:
        super().__init__(coordinator, f"filter_{filter_id}")
        self._filter_id = filter_id

    @property
    def available(self) -> bool:
        return (
            super().available and self._filter_id in self.coordinator.data.filter_counts
        )

    @property
    def name(self) -> str | None:
        return self.coordinator.data.filters.get(self._filter_id)

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.filter_counts.get(self._filter_id)


class NextEventSensor(_EasyVereinSensor):
    _attr_translation_key = "next_event"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: EasyVereinCoordinator) -> None:
        super().__init__(coordinator, "next_event")

    @property
    def _event(self) -> dict[str, Any] | None:
        events = next_events(self.coordinator.data.upcoming[None], dt_util.now())
        return events[0] if events else None

    @property
    def native_value(self) -> datetime | None:
        if event := self._event:
            return dt_util.as_local(dt_util.parse_datetime(event["start"]))
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event or {}
        return {"name": event.get("name"), "location": event.get("location_name")}
