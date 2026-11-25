"""Count sensors: members + one per custom filter."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import EasyVereinConfigEntry, EasyVereinCoordinator
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyVereinConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    # shortcut: filters created in easyVerein later only show up after reloading the integration
    async_add_entities(
        [MembersSensor(coordinator)]
        + [FilterSensor(coordinator, fid) for fid in coordinator.data["filters"]]
    )


class _CountSensor(CoordinatorEntity[EasyVereinCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: EasyVereinCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = device_info(coordinator.config_entry)


class MembersSensor(_CountSensor):
    _attr_translation_key = "members"
    _attr_icon = "mdi:account-group"

    def __init__(self, coordinator: EasyVereinCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_members"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data["members"]


class FilterSensor(_CountSensor):
    def __init__(self, coordinator: EasyVereinCoordinator, filter_id: int) -> None:
        super().__init__(coordinator)
        self._filter_id = filter_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_filter_{filter_id}"

    @property
    def _filter(self) -> dict | None:
        return self.coordinator.data["filters"].get(self._filter_id)

    @property
    def available(self) -> bool:
        return super().available and self._filter is not None

    @property
    def name(self) -> str | None:
        return self._filter["name"] if self._filter else None

    @property
    def native_value(self) -> int | None:
        return self._filter["count"] if self._filter else None
