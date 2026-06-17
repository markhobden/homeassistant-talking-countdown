"""Talking Countdown integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ANNOUNCEMENTS,
    CONF_DEFAULT_MINUTES,
    CONF_FINISHED_MESSAGE,
    CONF_MEDIA_PLAYER,
    CONF_TTS_ENTITY,
    DEFAULT_ANNOUNCEMENTS,
    DEFAULT_FINISHED_MESSAGE,
    DEFAULT_MINUTES,
    DOMAIN,
    SERVICE_CANCEL,
    SERVICE_CANCEL_ALL,
    SERVICE_START,
)
from .timer_manager import TalkingCountdownManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []

START_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Countdown"): cv.string,
        vol.Optional("minutes"): vol.Coerce(int),
        vol.Optional(CONF_ANNOUNCEMENTS): cv.string,
        vol.Optional(CONF_MEDIA_PLAYER): cv.entity_id,
        vol.Optional(CONF_TTS_ENTITY): cv.entity_id,
        vol.Optional(CONF_FINISHED_MESSAGE): cv.string,
    }
)

CANCEL_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Countdown"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Talking Countdown from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    defaults = _entry_defaults(entry)
    manager = TalkingCountdownManager(hass, defaults)
    hass.data[DOMAIN][entry.entry_id] = manager
    hass.data[DOMAIN]["manager"] = manager

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _register_services_once(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Talking Countdown."""
    manager: TalkingCountdownManager | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager is not None:
        await manager.async_cancel_all()

    domain_data = hass.data.get(DOMAIN, {})
    if domain_data.get("manager") is manager:
        domain_data.pop("manager", None)

    if not any(isinstance(value, TalkingCountdownManager) for value in domain_data.values()):
        for service in (SERVICE_START, SERVICE_CANCEL, SERVICE_CANCEL_ALL):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)

    return True


def _entry_defaults(entry: ConfigEntry) -> dict[str, Any]:
    """Return defaults from a config entry."""
    data = {**entry.data, **entry.options}
    return {
        CONF_TTS_ENTITY: data.get(CONF_TTS_ENTITY),
        CONF_MEDIA_PLAYER: data.get(CONF_MEDIA_PLAYER),
        CONF_ANNOUNCEMENTS: data.get(CONF_ANNOUNCEMENTS, DEFAULT_ANNOUNCEMENTS),
        CONF_FINISHED_MESSAGE: data.get(CONF_FINISHED_MESSAGE, DEFAULT_FINISHED_MESSAGE),
        CONF_DEFAULT_MINUTES: data.get(CONF_DEFAULT_MINUTES, DEFAULT_MINUTES),
    }


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update Talking Countdown defaults when options change."""
    manager = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if manager is not None:
        manager.defaults = _entry_defaults(entry)


def _register_services_once(hass: HomeAssistant) -> None:
    """Register services once per Home Assistant instance."""
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return

    async def async_start(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        defaults = manager.defaults
        minutes = call.data.get("minutes", defaults.get(CONF_DEFAULT_MINUTES, DEFAULT_MINUTES))
        await manager.async_start(
            name=call.data.get(CONF_NAME, "Countdown"),
            minutes=minutes,
            announcements=call.data.get(CONF_ANNOUNCEMENTS),
            media_player=call.data.get(CONF_MEDIA_PLAYER),
            tts_entity=call.data.get(CONF_TTS_ENTITY),
            finished_message=call.data.get(CONF_FINISHED_MESSAGE),
        )

    async def async_cancel(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        await manager.async_cancel(call.data.get(CONF_NAME, "Countdown"))

    async def async_cancel_all(call: ServiceCall) -> None:
        manager = _get_manager(hass)
        await manager.async_cancel_all()

    hass.services.async_register(DOMAIN, SERVICE_START, async_start, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL, async_cancel, schema=CANCEL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL_ALL, async_cancel_all)


def _get_manager(hass: HomeAssistant) -> TalkingCountdownManager:
    """Return the active countdown manager."""
    manager = hass.data.get(DOMAIN, {}).get("manager")
    if manager is None:
        raise RuntimeError("Talking Countdown is not configured")
    return manager
