"""Calendar entities: all events, plus one per easyVerein calendar."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import next_events
from .coordinator import EasyVereinConfigEntry, EasyVereinCoordinator
from .entity import device_info, sync_dynamic_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyVereinConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([EasyVereinCalendar(coordinator, None)])
    sync_dynamic_entities(
        hass,
        entry,
        coordinator,
        async_add_entities,
        domain="calendar",
        prefix="calendar_",
        current_ids=lambda data: set(data.calendars),
        factory=lambda calendar_id: EasyVereinCalendar(coordinator, calendar_id),
    )


class EasyVereinCalendar(CoordinatorEntity[EasyVereinCoordinator], CalendarEntity):
    """`calendar_id` None means all events, including those without a calendar."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyVereinCoordinator, calendar_id: int | None
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._calendar_id = calendar_id
        if calendar_id is None:
            self._attr_translation_key = "events"
            self._attr_unique_id = f"{entry.entry_id}_calendar"
        else:
            self._attr_unique_id = f"{entry.entry_id}_calendar_{calendar_id}"
        self._attr_device_info = device_info(entry)

    @property
    def name(self) -> str | None:
        if self._calendar_id is None:
            return super().name
        return self.coordinator.data.calendars.get(self._calendar_id)

    @property
    def event(self) -> CalendarEvent | None:
        """Current or next event, from the last poll."""
        upcoming = self.coordinator.data.upcoming.get(self._calendar_id, [])
        events = next_events(upcoming, dt_util.now())
        return _to_calendar_event(events[0]) if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        events = await self.coordinator.client.events(
            start_date, end_date, self._calendar_id
        )
        return [_to_calendar_event(e) for e in events]


def _to_calendar_event(item: dict) -> CalendarEvent:
    start = dt_util.parse_datetime(item["start"])
    end = dt_util.parse_datetime(item["end"])
    if not item.get("all_day"):
        start, end = dt_util.as_local(start), dt_util.as_local(end)
    else:
        # HA wants dates for all-day events; easyVerein's end is the last day, HA's is exclusive.
        start, end = start.date(), end.date() + timedelta(days=1)
    return CalendarEvent(
        start=start,
        end=end,
        summary=item["name"],
        description=item.get("description") or None,
        location=item.get("location_name") or None,
    )
