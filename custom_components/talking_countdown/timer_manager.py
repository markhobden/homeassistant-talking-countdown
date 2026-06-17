"""Timer management for Talking Countdown."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_FINISHED_MESSAGE, CONF_MEDIA_PLAYER, CONF_TTS_ENTITY

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CountdownTimer:
    """A running countdown timer."""

    name: str
    task: asyncio.Task[None]


class TalkingCountdownManager:
    """Manage named talking countdown timers."""

    def __init__(self, hass: HomeAssistant, defaults: dict[str, Any]) -> None:
        """Initialise the manager."""
        self.hass = hass
        self.defaults = defaults
        self._timers: dict[str, CountdownTimer] = {}

    async def async_start(
        self,
        *,
        name: str,
        minutes: int,
        announcements: str | None = None,
        media_player: str | None = None,
        tts_entity: str | None = None,
        finished_message: str | None = None,
    ) -> None:
        """Start or replace a named countdown."""
        normalised_name = _normalise_name(name)
        await self.async_cancel(normalised_name)

        total_seconds = max(1, int(minutes)) * 60
        announcement_minutes = parse_announcements(announcements or self.defaults.get("announcements", ""), int(minutes))
        resolved_media_player = media_player or self.defaults.get(CONF_MEDIA_PLAYER)
        resolved_tts_entity = tts_entity or self.defaults.get(CONF_TTS_ENTITY)
        resolved_finished_message = finished_message or self.defaults.get(CONF_FINISHED_MESSAGE) or "Time is up"

        task = self.hass.async_create_task(
            self._run_timer(
                name=normalised_name,
                total_seconds=total_seconds,
                announcement_minutes=announcement_minutes,
                media_player=resolved_media_player,
                tts_entity=resolved_tts_entity,
                finished_message=resolved_finished_message,
            )
        )
        self._timers[normalised_name] = CountdownTimer(name=normalised_name, task=task)

    async def async_cancel(self, name: str) -> None:
        """Cancel a named countdown."""
        normalised_name = _normalise_name(name)
        timer = self._timers.pop(normalised_name, None)
        if timer is None:
            return

        timer.task.cancel()
        try:
            await timer.task
        except asyncio.CancelledError:
            pass

    async def async_cancel_all(self) -> None:
        """Cancel all running countdowns."""
        names = list(self._timers)
        for name in names:
            await self.async_cancel(name)

    async def _run_timer(
        self,
        *,
        name: str,
        total_seconds: int,
        announcement_minutes: list[int],
        media_player: str | None,
        tts_entity: str | None,
        finished_message: str,
    ) -> None:
        """Run a countdown and make announcements."""
        try:
            elapsed = 0
            for remaining_minutes in sorted(announcement_minutes, reverse=True):
                announce_at = total_seconds - (remaining_minutes * 60)
                delay = announce_at - elapsed
                if delay > 0:
                    await asyncio.sleep(delay)
                    elapsed += delay
                await self._speak(
                    tts_entity=tts_entity,
                    media_player=media_player,
                    message=f"{name}: {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''} remaining",
                )

            final_delay = total_seconds - elapsed
            if final_delay > 0:
                await asyncio.sleep(final_delay)
            await self._speak(
                tts_entity=tts_entity,
                media_player=media_player,
                message=f"{name}: {finished_message}",
            )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Talking countdown '%s' failed", name)
        finally:
            self._timers.pop(name, None)

    async def _speak(self, *, tts_entity: str | None, media_player: str | None, message: str) -> None:
        """Speak a message using Home Assistant TTS."""
        if not tts_entity or not media_player:
            _LOGGER.warning("Cannot speak countdown message because TTS or media player is not configured")
            return

        domain, _, service = tts_entity.partition(".")
        if not domain or not service:
            _LOGGER.warning("Invalid TTS entity configured: %s", tts_entity)
            return

        await self.hass.services.async_call(
            domain,
            service,
            {
                "media_player_entity_id": media_player,
                "message": message,
            },
            blocking=False,
        )


def parse_announcements(value: str, total_minutes: int) -> list[int]:
    """Parse comma-separated announcement milestones."""
    result: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        try:
            minutes = int(part)
        except ValueError:
            continue
        if 0 < minutes <= total_minutes:
            result.add(minutes)
    return sorted(result, reverse=True)


def _normalise_name(name: str | None) -> str:
    """Normalise a timer name."""
    cleaned = (name or "Countdown").strip()
    return cleaned or "Countdown"
