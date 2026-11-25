"""API client and pure helpers, against a fake session."""

from datetime import UTC, date, datetime, timedelta

import pytest

from custom_components.easyverein import api


class FakeResponse:
    def __init__(self, status, payload):
        self.status, self._payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(self.status)

    async def json(self):
        return self._payload


class FakeSession:
    """Maps URL suffix -> (status, payload); records calls."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        key = next(k for k in self.routes if url.endswith(k))
        return FakeResponse(*self.routes[key])


def client(routes, token="tok"):
    return api.EasyVereinClient(FakeSession(routes), token)


async def test_count_asks_for_one_row_and_returns_count():
    c = client({"member": (200, {"count": 42, "results": []})})
    assert await c.count("member", custom_filter=7) == 42
    _, params, headers = c._session.calls[0]
    assert params == {"custom_filter": 7, "limit": 1, "show_count": "true"}
    assert headers["Authorization"] == "Bearer tok"


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, api.EasyVereinAuthError),
        (403, api.EasyVereinForbidden),
        (400, api.EasyVereinBadRequest),
    ],
)
async def test_status_codes_map_to_errors(status, error):
    with pytest.raises(error):
        await client({"member": (status, {})}).count("member")


async def test_403_on_refresh_means_expired_token():
    with pytest.raises(api.EasyVereinAuthError):
        await client({"refresh-token": (403, {})}).refresh_token()


async def test_refresh_token_replaces_token():
    c = client({"refresh-token": (200, {"Bearer": "new"})}, token="old")
    assert await c.refresh_token() == "new"
    assert c.token == "new"


async def test_custom_filters_paginates_and_skips_unsupported_models():
    c = client(
        {
            "custom-filter": (
                200,
                {
                    "next": "https://x/page2",
                    "results": [
                        {"id": 1, "name": "Anträge", "model": "userFilter"},
                        {"id": 2, "name": "Logs", "model": "loginLogsFilter"},
                    ],
                },
            ),
            "page2": (
                200,
                {
                    "next": None,
                    "results": [{"id": 3, "name": "Offen", "model": "invoiceFilter"}],
                },
            ),
        }
    )
    assert [f["id"] for f in await c.custom_filters()] == [1, 3]


async def test_upcoming_events_sorted_by_start_and_filtered_by_calendar():
    now = datetime(2026, 5, 1, tzinfo=UTC)
    c = client({"event": (200, {"results": [{"id": 1}]})})
    assert await c.upcoming_events(now, calendar=5, limit=3) == [{"id": 1}]
    _, params, _ = c._session.calls[0]
    assert params == {
        "end__gte": now.isoformat(),
        "ordering": "start",
        "limit": 3,
        "calendar": 5,
    }


def test_member_counts_separates_applicants_from_members():
    counts = api.member_counts(date(2026, 5, 31))
    assert counts["members"] == {"is_application": "false", "has_left": "false"}
    assert counts["applications"] == {"is_application": "true"}
    assert counts["resignations"]["resignation_notice_date__isnull"] == "false"
    assert counts["new_members"]["join_date__gte"] == "2026-05-01"


def test_next_events_skips_ended_sorts_and_accepts_naive_times():
    now = datetime(2026, 5, 1, 12, tzinfo=UTC)
    hour = timedelta(hours=1)

    def event(name, start, end):
        return {"name": name, "start": start.isoformat(), "end": end.isoformat()}

    events = [
        event("vorbei", now - 3 * hour, now - hour),
        event("später", now + 5 * hour, now + 6 * hour),
        event("läuft", now - hour, now + hour),
        {"name": "naiv", "start": "2026-05-01T20:00:00", "end": "2026-05-01T21:00:00"},
    ]
    assert [e["name"] for e in api.next_events(events, now, limit=5)] == [
        "läuft",
        "später",
        "naiv",
    ]
    assert api.next_events([], now) == []
