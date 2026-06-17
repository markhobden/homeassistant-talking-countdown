"""Config flow for Talking Countdown."""

from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

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
)

MAX_DEFAULT_MINUTES = 240


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Talking Countdown config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TalkingCountdownOptionsFlow:
        """Create the options flow."""
        return TalkingCountdownOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Talking Countdown",
                    data=_normalise_input(user_input),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_config_schema(user_input),
            errors=errors,
        )


class TalkingCountdownOptionsFlow(config_entries.OptionsFlow):
    """Handle Talking Countdown options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Talking Countdown options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data=_normalise_input(user_input),
                )

        values = user_input if user_input is not None else _entry_values(self._config_entry)
        return self.async_show_form(
            step_id="init",
            data_schema=_config_schema(values),
            errors=errors,
        )


def _entry_values(entry: ConfigEntry) -> dict[str, Any]:
    """Return the effective entry values."""
    return {**entry.data, **entry.options}


def _config_schema(values: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return the config flow schema."""
    defaults = {
        CONF_ANNOUNCEMENTS: DEFAULT_ANNOUNCEMENTS,
        CONF_FINISHED_MESSAGE: DEFAULT_FINISHED_MESSAGE,
        CONF_DEFAULT_MINUTES: DEFAULT_MINUTES,
    }
    if values is not None:
        defaults.update(values)

    return vol.Schema(
        {
            _required(CONF_TTS_ENTITY, defaults.get(CONF_TTS_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="tts")
            ),
            _required(CONF_MEDIA_PLAYER, defaults.get(CONF_MEDIA_PLAYER)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player")
            ),
            vol.Required(
                CONF_ANNOUNCEMENTS,
                default=defaults[CONF_ANNOUNCEMENTS],
            ): str,
            vol.Required(
                CONF_FINISHED_MESSAGE,
                default=defaults[CONF_FINISHED_MESSAGE],
            ): str,
            vol.Required(
                CONF_DEFAULT_MINUTES,
                default=defaults[CONF_DEFAULT_MINUTES],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=MAX_DEFAULT_MINUTES,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _required(key: str, default: Any | None) -> vol.Required:
    """Return a required schema marker with an optional default."""
    if default in (None, ""):
        return vol.Required(key)
    return vol.Required(key, default=default)


def _validate_input(user_input: Mapping[str, Any]) -> dict[str, str]:
    """Validate user input."""
    errors: dict[str, str] = {}

    if not _valid_entity_id(user_input.get(CONF_TTS_ENTITY), "tts"):
        errors[CONF_TTS_ENTITY] = "invalid_tts_entity"

    if not _valid_entity_id(user_input.get(CONF_MEDIA_PLAYER), "media_player"):
        errors[CONF_MEDIA_PLAYER] = "invalid_media_player"

    if _parse_announcements(str(user_input.get(CONF_ANNOUNCEMENTS, ""))) is None:
        errors[CONF_ANNOUNCEMENTS] = "invalid_announcements"

    try:
        default_minutes = int(user_input[CONF_DEFAULT_MINUTES])
    except (KeyError, TypeError, ValueError):
        errors[CONF_DEFAULT_MINUTES] = "invalid_default_minutes"
    else:
        if not 1 <= default_minutes <= MAX_DEFAULT_MINUTES:
            errors[CONF_DEFAULT_MINUTES] = "invalid_default_minutes"

    if not str(user_input.get(CONF_FINISHED_MESSAGE, "")).strip():
        errors[CONF_FINISHED_MESSAGE] = "empty_finished_message"

    return errors


def _normalise_input(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalised config entry data."""
    return {
        CONF_TTS_ENTITY: str(user_input[CONF_TTS_ENTITY]),
        CONF_MEDIA_PLAYER: str(user_input[CONF_MEDIA_PLAYER]),
        CONF_ANNOUNCEMENTS: _normalise_announcements(str(user_input[CONF_ANNOUNCEMENTS])),
        CONF_FINISHED_MESSAGE: str(user_input[CONF_FINISHED_MESSAGE]).strip(),
        CONF_DEFAULT_MINUTES: int(user_input[CONF_DEFAULT_MINUTES]),
    }


def _valid_entity_id(value: Any, domain: str) -> bool:
    """Return whether the value is a valid entity ID for the expected domain."""
    if not isinstance(value, str):
        return False

    try:
        entity_id = cv.entity_id(value)
    except vol.Invalid:
        return False

    return entity_id.split(".", 1)[0] == domain


def _normalise_announcements(value: str) -> str:
    """Return canonical comma-separated announcement milestones."""
    parsed = _parse_announcements(value)
    if parsed is None:
        return DEFAULT_ANNOUNCEMENTS
    return ",".join(str(minutes) for minutes in parsed)


def _parse_announcements(value: str) -> list[int] | None:
    """Parse comma-separated positive minute milestones."""
    milestones: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue

        try:
            minutes = int(part)
        except ValueError:
            return None

        if minutes <= 0:
            return None

        milestones.add(minutes)

    return sorted(milestones, reverse=True)
