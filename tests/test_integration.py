"""Integration tests against a fake easyVerein API (needs Home Assistant)."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.easyverein.const import DOMAIN

CUSTOM_FILTERS = [
    {"id": 1, "name": "Offene Rechnungen", "model": "invoiceFilter"},
    {"id": 2, "name": "Vorstand", "model": "userFilter"},
    {"id": 3, "name": "Logs", "model": "loginLogsFilter"},  # unsupported, skipped
]


def fake_api(forbidden: tuple[str, ...] = ()):
    """Returns an aiohttp mock side effect that behaves like the easyVerein API."""
    start = dt_util.now() + timedelta(days=1)
    event = {
        "id": 10,
        "name": "Training",
        "start": start.isoformat(),
        "end": (start + timedelta(hours=2)).isoformat(),
        "all_day": False,
        "location_name": "Halle",
    }

    async def handler(method, url, data):
        endpoint = url.path.rstrip("/").rsplit("/", 1)[-1]
        query = url.query
        if endpoint in forbidden:
            return AiohttpClientMockResponse(method, url, status=403, json={})
        if endpoint == "refresh-token":
            body = {"Bearer": "tok"}
        elif endpoint == "member":
            if query.get("is_application") == "true":
                count = 4
            elif "resignation_notice_date__isnull" in query:
                count = 2
            elif "join_date__gte" in query:
                count = 6
            elif query.get("custom_filter") == "2":
                count = 9
            else:
                count = 120
            body = {"count": count, "results": [], "next": None}
        elif endpoint == "invoice":
            body = {"count": 3, "results": [], "next": None}
        elif endpoint == "custom-filter":
            body = {"results": CUSTOM_FILTERS, "next": None}
        elif endpoint == "calendar":
            body = {"results": [{"id": 5, "name": "Jugend"}], "next": None}
        elif endpoint == "event":
            body = {"results": [event], "next": None}
        else:
            return AiohttpClientMockResponse(method, url, status=404, json={})
        return AiohttpClientMockResponse(method, url, json=body)

    return handler


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={"token": "tok"})
    entry.add_to_hass(hass)
    return entry


async def setup(hass, entry, aioclient_mock: AiohttpClientMocker, **kwargs):
    import re

    aioclient_mock.get(re.compile(r".*"), side_effect=fake_api(**kwargs))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def state_of(hass, entry, domain, suffix):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        domain, DOMAIN, f"{entry.entry_id}_{suffix}"
    )
    return hass.states.get(entity_id) if entity_id else None


async def test_sensors(hass, entry, aioclient_mock):
    await setup(hass, entry, aioclient_mock)

    assert state_of(hass, entry, "sensor", "members").state == "120"
    assert state_of(hass, entry, "sensor", "applications").state == "4"
    assert state_of(hass, entry, "sensor", "resignations").state == "2"
    assert state_of(hass, entry, "sensor", "new_members").state == "6"
    assert state_of(hass, entry, "sensor", "filter_1").state == "3"
    assert (
        state_of(hass, entry, "sensor", "filter_1").name
        == "easyVerein Offene Rechnungen"
    )
    assert state_of(hass, entry, "sensor", "filter_2").state == "9"
    assert state_of(hass, entry, "sensor", "filter_3") is None  # unsupported model
    next_event = state_of(hass, entry, "sensor", "next_event")
    assert next_event.attributes["name"] == "Training"
    assert next_event.attributes["location"] == "Halle"


async def test_calendars(hass, entry, aioclient_mock):
    await setup(hass, entry, aioclient_mock)

    all_events = state_of(hass, entry, "calendar", "calendar")
    youth = state_of(hass, entry, "calendar", "calendar_5")
    assert all_events.attributes["message"] == "Training"
    assert youth.name == "easyVerein Jugend"
    assert youth.attributes["message"] == "Training"


async def test_missing_rights_only_hide_what_is_forbidden(hass, entry, aioclient_mock):
    await setup(hass, entry, aioclient_mock, forbidden=("invoice", "calendar"))

    assert state_of(hass, entry, "sensor", "members").state == "120"
    assert state_of(hass, entry, "sensor", "filter_1") is None
    assert state_of(hass, entry, "sensor", "filter_2").state == "9"
    assert state_of(hass, entry, "calendar", "calendar_5") is None
    assert state_of(hass, entry, "calendar", "calendar") is not None


async def test_options_hide_filter_and_change_interval(hass, entry, aioclient_mock):
    await setup(hass, entry, aioclient_mock)
    assert state_of(hass, entry, "sensor", "filter_2") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 10, "excluded_filters": ["2"]}
    )
    await hass.async_block_till_done()

    assert state_of(hass, entry, "sensor", "filter_2") is None
    assert state_of(hass, entry, "sensor", "filter_1") is not None
    assert entry.runtime_data.update_interval == timedelta(minutes=10)


async def test_config_flow(hass, aioclient_mock):
    import re

    aioclient_mock.get(re.compile(r".*"), side_effect=fake_api())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"token": " tok "}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {"token": "tok"}


async def test_config_flow_invalid_token(hass, aioclient_mock):
    aioclient_mock.get(
        "https://easyverein.com/api/v3.0/refresh-token", status=401, json={}
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"token": "bad"}
    )
    assert result["errors"] == {"base": "invalid_auth"}
