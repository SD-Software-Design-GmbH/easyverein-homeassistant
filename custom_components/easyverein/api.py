"""Minimal async client for the easyVerein REST API (v3.0). No Home Assistant imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import BASE_URL, MODEL_ENDPOINTS

PAGE_LIMIT = 100  # API maximum


class EasyVereinAuthError(Exception):
    """Token rejected (invalid or expired)."""


class EasyVereinForbidden(Exception):
    """Token is valid, but its user may not read this endpoint."""


class EasyVereinClient:
    def __init__(self, session: Any, token: str) -> None:
        self._session = session
        self.token = token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with self._session.get(
            path if path.startswith("http") else BASE_URL + path,
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
        ) as resp:
            if resp.status == 401:
                raise EasyVereinAuthError
            if resp.status == 403:
                raise EasyVereinForbidden
            resp.raise_for_status()
            return await resp.json()

    async def refresh_token(self) -> str:
        """Ask for a fresh token. Returns the same one while the current is young enough."""
        try:
            data = await self._get("refresh-token")
        except EasyVereinForbidden as err:  # the server answers 403 for expired tokens here
            raise EasyVereinAuthError from err
        self.token = data["Bearer"]
        return self.token

    async def count(self, endpoint: str, **params: Any) -> int:
        """Number of entries of `endpoint` matching `params`, via one tiny request."""
        data = await self._get(
            endpoint, {**params, "limit": 1, "show_count": "true"}
        )
        return data["count"]

    async def custom_filters(self) -> list[dict[str, Any]]:
        """All custom filters whose model we can count (see MODEL_ENDPOINTS)."""
        filters = [
            f
            async for f in self._paginate("custom-filter", {"limit": PAGE_LIMIT})
            if f.get("model") in MODEL_ENDPOINTS
        ]
        return filters

    async def events(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Events overlapping [start, end]."""
        params = {
            "start__lte": end.isoformat(),
            "end__gte": start.isoformat(),
            "limit": PAGE_LIMIT,
        }
        return [e async for e in self._paginate("event", params)]

    async def _paginate(self, path: str, params: dict[str, Any]):
        data = await self._get(path, params)
        while True:
            for item in data["results"]:
                yield item
            if not data.get("next"):
                return
            data = await self._get(data["next"])  # `next` is a full URL incl. params
