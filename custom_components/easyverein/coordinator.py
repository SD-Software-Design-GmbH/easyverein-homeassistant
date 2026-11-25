"""Data update coordinator: polls all counts in one go."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EasyVereinAuthError, EasyVereinClient, EasyVereinForbidden
from .const import DOMAIN, MODEL_ENDPOINTS, TOKEN_REFRESH_INTERVAL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type EasyVereinConfigEntry = ConfigEntry[EasyVereinCoordinator]


class EasyVereinCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data: {"members": int | None, "filters": {id: {"name": str, "count": int}}}."""

    config_entry: EasyVereinConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EasyVereinConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = EasyVereinClient(
            async_get_clientsession(hass), entry.data[CONF_TOKEN]
        )
        self._last_token_refresh: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self._refresh_token_if_due()
            return {
                "members": await self._count_or_none(
                    "member", resignation_date__isnull="true"
                ),
                "filters": await self._filter_counts(),
            }
        except EasyVereinAuthError as err:
            raise ConfigEntryAuthFailed from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(err) from err

    async def _count_or_none(self, endpoint: str, **params: Any) -> int | None:
        try:
            return await self.client.count(endpoint, **params)
        except EasyVereinForbidden:
            return None  # the token's user lacks the read right for this module

    async def _filter_counts(self) -> dict[int, dict[str, Any]]:
        try:
            filters = await self.client.custom_filters()
        except EasyVereinForbidden:
            return {}  # custom filters need a user with chairman rights
        counts = {}
        for f in filters:
            count = await self._count_or_none(
                MODEL_ENDPOINTS[f["model"]], custom_filter=f["id"]
            )
            if count is not None:
                counts[f["id"]] = {"name": f["name"], "count": count}
        return counts

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
