"""The Metservice Tides integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from .fetcher import fetch_metservice_tide, MetserviceTideApi

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Metservice Tides from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    _LOGGER.warning("NP_D async_setup_entry")

    async def async_update_data():
        """Fetch new data from the MetService."""
        _LOGGER.warning(f"NP_D fetch data from coordinator, {entry.as_dict()}")
        async with async_timeout.timeout(10):
            return await MetserviceTideApi().async_request()

    async def async_calc_data():
        return {}

    fetch_coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="metservice-tides-fetch",
        update_interval=timedelta(hours=1),
        update_method=async_update_data,
    )
    calculate_coordinator: DataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="metservice-tides-calculate",
        update_interval=timedelta(minutes=1),
        update_method=async_calc_data,
    )
    hass.data[DOMAIN]["fetch_coordinator"] = fetch_coordinator
    hass.data[DOMAIN]["calculate_coordinator"] = calculate_coordinator
    await fetch_coordinator.async_config_entry_first_refresh()
    await calculate_coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
