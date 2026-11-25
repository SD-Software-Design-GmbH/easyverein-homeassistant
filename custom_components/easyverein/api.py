"""Minimal async client for the easyVerein REST API (v3.0). No Home Assistant imports."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from .const import BASE_URL, MODEL_ENDPOINTS

PAGE_LIMIT = 100  # API maximum
TIMEOUT = 30  # seconds per request


class EasyVereinAuthError(Exception):
    """Token rejected (invalid or expired)."""


class EasyVereinForbidden(Exception):
    """Token is valid, but its user may not read this endpoint."""


class EasyVereinBadRequest(Exception):
    """The API rejected the request (e.g. an unknown filter parameter)."""


def member_counts(today: date) -> dict[str, dict[str, str]]:
    """Built-in counters on the `member` endpoint: key -> query parameters.

    An applicant has `is_application=true` until the application is accepted.
    """
    active = {"is_application": "false", "has_left": "false"}
    return {
        "members": active,
        "applications": {"is_application": "true"},
        "resignations": {**active, "resignation_notice_date__isnull": "false"},
        "new_members": {
            **active,
            "join_date__gte": (today - timedelta(days=30)).isoformat(),
        },
    }


def next_events(
    events: list[dict[str, Any]], now: datetime, limit: int = 1
) -> list[dict[str, Any]]:
    """The first `limit` events (sorted by start) that have not ended yet."""

    def parse(value: str) -> datetime:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=now.tzinfo)

    not_ended = [e for e in events if parse(e["end"]) > now]
    not_ended.sort(key=lambda e: parse(e["start"]))
    return not_ended[:limit]


class EasyVereinClient:
    def __init__(self, session: Any, token: str) -> None:
        self._session = session
        self.token = token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with (
            asyncio.timeout(TIMEOUT),
            self._session.get(
                path if path.startswith("http") else BASE_URL + path,
                params=params,
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp,
        ):
            if resp.status == 401:
                raise EasyVereinAuthError
            if resp.status == 403:
                raise EasyVereinForbidden
            if resp.status == 400:
                raise EasyVereinBadRequest
            resp.raise_for_status()
            return await resp.json()

    async def refresh_token(self) -> str:
        """Ask for a fresh token. Returns the same one while the current is young enough."""
        try:
            data = await self._get("refresh-token")
        except (
            EasyVereinForbidden
        ) as err:  # the server answers 403 for expired tokens here
            raise EasyVereinAuthError from err
        self.token = data["Bearer"]
        return self.token

    async def count(self, endpoint: str, **params: Any) -> int:
        """Number of entries of `endpoint` matching `params`, via one tiny request."""
        data = await self._get(endpoint, {**params, "limit": 1, "show_count": "true"})
        return data["count"]

    async def custom_filters(self) -> list[dict[str, Any]]:
        """All custom filters whose model we can count (see MODEL_ENDPOINTS)."""
        filters = [
            f
            async for f in self._paginate("custom-filter", {"limit": PAGE_LIMIT})
            if f.get("model") in MODEL_ENDPOINTS
        ]
        return filters

    async def calendars(self) -> list[dict[str, Any]]:
        return [c async for c in self._paginate("calendar", {"limit": PAGE_LIMIT})]

    async def events(
        self, start: datetime, end: datetime, calendar: int | None = None
    ) -> list[dict[str, Any]]:
        """Events overlapping [start, end], optionally of one easyVerein calendar."""
        params: dict[str, Any] = {
            "start__lte": end.isoformat(),
            "end__gte": start.isoformat(),
            "limit": PAGE_LIMIT,
        }
        if calendar is not None:
            params["calendar"] = calendar
        return [e async for e in self._paginate("event", params)]

    async def upcoming_events(
        self, now: datetime, calendar: int | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        """The next events that have not ended yet (first page only)."""
        params: dict[str, Any] = {
            "end__gte": now.isoformat(),
            "ordering": "start",
            "limit": limit,
        }
        if calendar is not None:
            params["calendar"] = calendar
        return (await self._get("event", params))["results"]

    async def _paginate(self, path: str, params: dict[str, Any]):
        data = await self._get(path, params)
        while True:
            for item in data["results"]:
                yield item
            if not data.get("next"):
                return
            data = await self._get(data["next"])  # `next` is a full URL incl. params
