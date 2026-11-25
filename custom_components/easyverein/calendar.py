"""Calendar entity: all easyVerein events, fetched on demand for the requested window."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import EasyVereinConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyVereinConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EasyVereinCalendar(entry)])


class EasyVereinCalendar(CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Termine"

    def __init__(self, entry: EasyVereinConfigEntry) -> None:
        self._client = entry.runtime_data.client
        self._attr_unique_id = f"{entry.entry_id}_calendar"

    # shortcut: no "next event" state (always off); add via a cached upcoming-events fetch if wanted
    @property
    def event(self) -> CalendarEvent | None:
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _to_calendar_event(e) for e in await self._client.events(start_date, end_date)
        ]


def _to_calendar_event(item: dict) -> CalendarEvent:
    start = dt_util.parse_datetime(item["start"])
    end = dt_util.parse_datetime(item["end"])
    if item.get("all_day"):
        # HA wants dates for all-day events; easyVerein's end is the last day, HA's is exclusive.
        start, end = start.date(), end.date() + timedelta(days=1)
    return CalendarEvent(
        start=start,
        end=end,
        summary=item["name"],
        description=item.get("description") or None,
        location=item.get("location_name") or None,
    )
