"""Data update coordinator: polls all counts and upcoming events in one go."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    EasyVereinAuthError,
    EasyVereinBadRequest,
    EasyVereinClient,
    EasyVereinForbidden,
    member_counts,
)
from .const import (
    CONF_EXCLUDED_FILTERS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MODEL_ENDPOINTS,
    TOKEN_REFRESH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type EasyVereinConfigEntry = ConfigEntry[EasyVereinCoordinator]


@dataclass
class EasyVereinData:
    counts: dict[str, int | None]  # built-in member counters, None if not readable
    filters: dict[int, str]  # all custom filters: id -> name
    filter_counts: dict[int, int]  # only filters that get a sensor
    calendars: dict[int, str]  # easyVerein calendars: id -> name
    upcoming: dict[int | None, list[dict[str, Any]]]  # per calendar, None = all


class EasyVereinCoordinator(DataUpdateCoordinator[EasyVereinData]):
    config_entry: EasyVereinConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EasyVereinConfigEntry) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = EasyVereinClient(
            async_get_clientsession(hass), entry.data[CONF_TOKEN]
        )
        self.options = dict(entry.options)
        self._last_token_refresh: datetime | None = None

    async def _async_update_data(self) -> EasyVereinData:
        try:
            await self._refresh_token_if_due()
            return await self._fetch()
        except EasyVereinAuthError as err:
            raise ConfigEntryAuthFailed from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(err) from err

    async def _fetch(self) -> EasyVereinData:
        now = dt_util.now()
        counts = {
            key: await self._count_or_none("member", **params)
            for key, params in member_counts(now.date()).items()
        }
        filters, filter_counts = await self._filters()
        try:
            calendars = {c["id"]: c["name"] for c in await self.client.calendars()}
        except EasyVereinForbidden:
            calendars = {}  # listing calendars needs the member area module
        upcoming = {key: await self._upcoming(key, now) for key in (None, *calendars)}
        return EasyVereinData(counts, filters, filter_counts, calendars, upcoming)

    async def _count_or_none(self, endpoint: str, **params: Any) -> int | None:
        try:
            return await self.client.count(endpoint, **params)
        except EasyVereinForbidden:
            return None  # the token's user lacks the read right for this module
        except EasyVereinBadRequest:
            _LOGGER.warning("easyVerein rejected %s with %s", endpoint, params)
            return None

    async def _filters(self) -> tuple[dict[int, str], dict[int, int]]:
        try:
            filters = await self.client.custom_filters()
        except EasyVereinForbidden:
            return {}, {}  # custom filters need a user with chairman rights
        excluded = set(self.options.get(CONF_EXCLUDED_FILTERS, []))
        counts = {}
        for f in filters:
            if str(f["id"]) in excluded:
                continue
            count = await self._count_or_none(
                MODEL_ENDPOINTS[f["model"]], custom_filter=f["id"]
            )
            if count is not None:
                counts[f["id"]] = count
        return {f["id"]: f["name"] for f in filters}, counts

    async def _upcoming(self, calendar: int | None, now: datetime) -> list[dict]:
        try:
            return await self.client.upcoming_events(now, calendar)
        except (EasyVereinForbidden, EasyVereinBadRequest):
            return []

    async def _refresh_token_if_due(self) -> None:
        now = dt_util.utcnow()
        if (
            self._last_token_refresh
            and now - self._last_token_refresh < TOKEN_REFRESH_INTERVAL
        ):
            return
        old = self.client.token
        new = await self.client.refresh_token()
        self._last_token_refresh = now
        if new != old:
            # The old token is invalid now, so persist the new one immediately.
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, CONF_TOKEN: new}
            )
