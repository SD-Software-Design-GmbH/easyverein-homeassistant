"""Shared helpers for the entity platforms."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EasyVereinConfigEntry, EasyVereinCoordinator, EasyVereinData


def device_info(entry: EasyVereinConfigEntry) -> DeviceInfo:
    """One "easyVerein" service device that all entities belong to."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="easyVerein",
        name="easyVerein",
    )


@callback
def sync_dynamic_entities(
    hass: HomeAssistant,
    entry: EasyVereinConfigEntry,
    coordinator: EasyVereinCoordinator,
    async_add_entities: AddEntitiesCallback,
    *,
    domain: str,
    prefix: str,
    current_ids: Callable[[EasyVereinData], set[int]],
    factory: Callable[[int], Entity],
) -> None:
    """Add entities for ids that appear later, remove those of ids that vanish.

    Unique ids look like `<entry_id>_<prefix><id>`.
    """
    known: set[int] = set()
    unique_prefix = f"{entry.entry_id}_{prefix}"
    registry = er.async_get(hass)

    @callback
    def _sync() -> None:
        ids = current_ids(coordinator.data)
        if new := ids - known:
            async_add_entities(factory(i) for i in sorted(new))
            known.update(new)
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.domain != domain or not reg_entry.unique_id.startswith(
                unique_prefix
            ):
                continue
            entity_id = int(reg_entry.unique_id.removeprefix(unique_prefix))
            if entity_id not in ids:
                registry.async_remove(reg_entry.entity_id)
                known.discard(entity_id)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))
