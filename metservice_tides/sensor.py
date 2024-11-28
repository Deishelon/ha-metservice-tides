"""Platform for sensor integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Callable

from . import DOMAIN
from .fetcher import TidesData, TideInfo
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass, SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TidesEntityDescriptionMixin:
    """Class for keys required by AirQ entity."""

    value: Callable[[TidesData], float | int | None]


@dataclass(frozen=True)
class TidesEntityDescription(SensorEntityDescription, TidesEntityDescriptionMixin):
    """Describes AirQ sensor entity."""


def get_next_tides(tide_info_list: list[TideInfo]):
    sorted_tide_info_list = sorted(tide_info_list, key=lambda x: x.timestamp)

    current_time = datetime.now().timestamp()  # Replace this with your desired current time

    _LOGGER.warning(f"NP_D Doing filtering, looking for above {current_time}")

    next_low_tide = None
    next_high_tide = None

    for tide_info in sorted_tide_info_list:
        if tide_info.type == 'LOW' and next_low_tide is None and tide_info.timestamp > current_time:
            next_low_tide = tide_info
        elif tide_info.type == 'HIGH' and next_high_tide is None and tide_info.timestamp > current_time:
            next_high_tide = tide_info

    return next_low_tide, next_high_tide


def get_closest_tides(tide_info_list: list[TideInfo]):
    current_time = datetime.now().timestamp()
    sorted_tide_info_list = sorted(tide_info_list, key=lambda x: abs(current_time - x.timestamp))

    if sorted_tide_info_list[0].type == "LOW":
        # low, high
        return sorted_tide_info_list[0], sorted_tide_info_list[1]
    else:
        # low, high
        return sorted_tide_info_list[1], sorted_tide_info_list[0]


def calculate_tide_position(tide1: TideInfo, tide2: TideInfo):
    target_timestamp = datetime.now().timestamp()

    # Calculate the time difference between tide1 and tide2
    total_time_difference = abs(tide2.timestamp - tide1.timestamp)

    # Calculate the time difference between target_timestamp and tide1
    time_difference_target = abs(target_timestamp - tide1.timestamp)

    # Calculate the tide position as a percentage
    tide_position_percent = (time_difference_target / total_time_difference) * 100

    return tide_position_percent

def calculate_tide_radial_position(tide1: TideInfo, tide2: TideInfo):
    now = datetime.now().timestamp()

    high = tide2.timestamp
    low = tide1.timestamp

    if (high - low) > 0:
        return 50-(((low - now)/(high - low)) * 50)
    else:
        return 100 - (((high - now) / (low - high)) * 50)


FETCHED_SENSOR_TYPES: list[TidesEntityDescription] = [
    TidesEntityDescription(
        key="next_low_tide_time",
        name="Next Low Tide Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda data: datetime.fromisoformat(get_next_tides(data.tides)[0].time),
    ),
    TidesEntityDescription(
        key="next_high_tide_time",
        name="Next High Tide Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda data: datetime.fromisoformat(get_next_tides(data.tides)[1].time),
    ),
    TidesEntityDescription(
        key="next_low_tide_height",
        name="Next Low Tide Height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        value=lambda data: get_next_tides(data.tides)[0].height,
    ),
    TidesEntityDescription(
        key="next_high_tide_height",
        name="Next High Tide Height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        value=lambda data: get_next_tides(data.tides)[1].height,
    ),

    TidesEntityDescription(
        key="low_tide_time",
        name="Low Tide Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda data: datetime.fromisoformat(get_closest_tides(data.tides)[0].time),
    ),
    TidesEntityDescription(
        key="high_tide_time",
        name="High Tide Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda data: datetime.fromisoformat(get_closest_tides(data.tides)[1].time),
    ),
    TidesEntityDescription(
        key="low_tide_height",
        name="Low Tide Height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        value=lambda data: get_closest_tides(data.tides)[0].height,
    ),
    TidesEntityDescription(
        key="high_tide_height",
        name="High Tide Height",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        value=lambda data: get_closest_tides(data.tides)[1].height,
    ),
]

CALCULATED_SENSOR_TYPES: list[TidesEntityDescription] = [
    TidesEntityDescription(
        key="tide_position",
        name="Tide Position",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value=lambda data: calculate_tide_position(get_closest_tides(data.tides)[0], get_closest_tides(data.tides)[1]),
    ),
    TidesEntityDescription(
        key="tide_radial_position",
        name="Tide Radial Position",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value=lambda data: calculate_tide_radial_position(get_closest_tides(data.tides)[0], get_closest_tides(data.tides)[1]),
    ),
]


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the Wall Connector sensor devices."""
    fetch_coordinator = hass.data[DOMAIN]["fetch_coordinator"]
    calculate_coordinator = hass.data[DOMAIN]["calculate_coordinator"]

    entities: list[SensorEntity] = []

    for description in FETCHED_SENSOR_TYPES:
        entities.append(TidesSensor(description.name, fetch_coordinator, description, config_entry.data["station_id"]))

    for description in CALCULATED_SENSOR_TYPES:
        entities.append(TideCalculatedSensor(description.name, calculate_coordinator, fetch_coordinator, description, config_entry.data["station_id"]))

    async_add_entities(entities)


class TidesSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_has_entity_name = True

    def __init__(
            self,
            name: str,
            coordinator: DataUpdateCoordinator,
            description: TidesEntityDescription,
            station_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._name = name
        self.entity_description: TidesEntityDescription = description

        self._attr_unique_id = f"{station_id}-{description.key}"
        self._attr_native_value = description.value(coordinator.data)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value(self.coordinator.data)
        self.async_write_ha_state()

class TideCalculatedSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_has_entity_name = True

    def __init__(
            self,
            name: str,
            calculate_coordinator: DataUpdateCoordinator,
            fetch_coordinator: DataUpdateCoordinator,
            description: TidesEntityDescription,
            station_id: str,
    ) -> None:
        super().__init__(calculate_coordinator)
        self._fetch_coordinator = fetch_coordinator
        self._name = name
        self.entity_description: TidesEntityDescription = description

        self._attr_unique_id = f"{station_id}-{description.key}"
        self._attr_native_value = description.value(fetch_coordinator.data)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value(self._fetch_coordinator.data)
        self.async_write_ha_state()