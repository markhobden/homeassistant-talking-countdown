# Talking Countdown Requirements

## Goal

Create a HACS-compatible Home Assistant custom integration that provides named countdown timers with spoken remaining-time announcements.

The integration should be usable by non-technical Home Assistant users while still exposing clean services for automations, dashboards, and Assist.

## MVP Scope

The first testable version should provide a backend-only MVP that can be installed through HACS, configured through the Home Assistant UI, and controlled through services.

### MVP User Story

As a Home Assistant user, I want to start a countdown timer and hear spoken announcements at configurable remaining-time milestones so that I do not need to keep checking a screen.

Example:

```yaml
service: talking_countdown.start
data:
  name: Oven
  minutes: 30
  announcements: "20,10,5,3,2,1"
```

Expected speech:

- "Oven: 20 minutes remaining"
- "Oven: 10 minutes remaining"
- "Oven: 5 minutes remaining"
- "Oven: 3 minutes remaining"
- "Oven: 2 minutes remaining"
- "Oven: 1 minute remaining"
- "Oven: Time is up"

## MVP Functional Requirements

### Installation

- The integration must be installable as a HACS custom repository.
- The integration must live under `custom_components/talking_countdown`.
- The integration must include valid HACS metadata.
- The integration must include a valid Home Assistant `manifest.json`.

### Configuration

The integration must support setup from **Settings -> Devices & Services** using a config flow.

The config flow must collect:

- Default TTS entity, for example `tts.home_assistant_cloud`
- Default media player entity, for example `media_player.kitchen_speaker`
- Default announcement milestones, for example `20,10,5,3,2,1`
- Default finished message, for example `Time is up`
- Default timer duration in minutes

### Services

The integration must expose these services:

#### `talking_countdown.start`

Starts or replaces a named countdown.

Fields:

- `name` string, optional, default `Countdown`
- `minutes` integer, required if no default duration is configured
- `announcements` string, optional, comma-separated minutes remaining
- `media_player` string, optional override
- `tts_entity` string, optional override
- `finished_message` string, optional override

Acceptance criteria:

- Starting a countdown schedules all valid announcements.
- Announcement milestones greater than the total timer duration are ignored.
- Duplicate or invalid milestones are ignored.
- Starting a timer with an existing name replaces the previous timer.
- The integration announces the finished message when the countdown completes.

#### `talking_countdown.cancel`

Cancels a named countdown.

Fields:

- `name` string, optional, default `Countdown`

Acceptance criteria:

- Cancelling an active countdown stops future announcements.
- Cancelling a missing countdown does not raise an error.

#### `talking_countdown.cancel_all`

Cancels all active countdowns.

Acceptance criteria:

- All scheduled announcements are cancelled.
- No further speech occurs for cancelled countdowns.

### Speech

- Speech should be performed using Home Assistant's TTS service model.
- The integration should call the configured TTS entity and pass the selected media player entity.
- Announcement text should include the timer name.
- Singular and plural minute wording should be handled correctly.

Examples:

- `Oven: 1 minute remaining`
- `Oven: 5 minutes remaining`
- `Oven: Time is up`

### Timer Behaviour

- Multiple named timers should be supported.
- A timer name should uniquely identify a countdown.
- Timers should run asynchronously without blocking Home Assistant.
- Timer tasks should be cancelled cleanly when Home Assistant unloads the integration.
- The integration should handle Home Assistant shutdown/reload without leaving orphaned tasks.

## Dashboard Requirements

After the backend MVP is working, provide a dashboard UI.

### Dashboard User Story

As a Home Assistant user, I want a dashboard panel where I can enter a timer name, choose a duration, choose a speaker, and start or cancel a talking countdown.

### Dashboard Features

- Timer name input
- Duration input
- Speaker selector
- Announcement milestones input
- Start button
- Cancel button
- Active timer list
- Remaining time display
- Clear visual indication when no timers are active

## Entity Requirements

After the backend MVP, expose Home Assistant entities for dashboard and automation use.

Preferred entities:

- `sensor.talking_countdown_active_timers`
- `sensor.talking_countdown_next_timer`
- Optional per-timer entities in a later version

The first entity implementation can be minimal.

## Assist Requirements

After the dashboard is working, add Assist support.

Example intents:

- "Start an oven timer for 30 minutes"
- "Cancel the oven timer"
- "How long is left on the oven timer?"

Assist support is not required for the MVP.

## Non-Functional Requirements

### Reliability

- The integration must not block the Home Assistant event loop.
- Timers must use asynchronous Home Assistant-safe scheduling.
- Errors from TTS calls should be logged but should not crash the integration.

### Usability

- Sensible defaults should be provided.
- Invalid announcement input should be tolerated where possible.
- Config flow labels should be clear.
- README examples should be copy-paste friendly.

### Compatibility

- Target Home Assistant version: 2024.6.0 or later.
- No external Python dependencies for MVP.
- HACS installable as an integration.

## Out of Scope for MVP

- Frontend custom panel
- Assist intents
- Persistent timers across Home Assistant restarts
- Per-user voice preferences
- Complex recurring timers
- Mobile push notifications
- Calendar integration
- Timer history/statistics

## Suggested Milestones

### Milestone 1: Backend MVP

- Config flow
- Service registration
- Start/cancel/cancel_all services
- Async countdown manager
- TTS announcements
- README installation and service examples

### Milestone 2: Entities

- Active timers sensor
- Next timer sensor
- Attributes containing timer state

### Milestone 3: Dashboard

- Lovelace custom card or panel
- Start/cancel controls
- Active timer list

### Milestone 4: Assist

- Start timer intent
- Cancel timer intent
- Time remaining intent

### Milestone 5: Polish

- Tests
- Release workflow
- HACS validation
- Screenshots
- Better documentation

## Initial Test Plan

### Manual Test 1: Basic Countdown

1. Install integration through HACS.
2. Restart Home Assistant.
3. Add integration through Settings -> Devices & Services.
4. Configure a working TTS entity and media player.
5. Call:

```yaml
service: talking_countdown.start
data:
  name: Test
  minutes: 2
  announcements: "1"
```

Expected result:

- At 1 minute remaining, Home Assistant announces `Test: 1 minute remaining`.
- At completion, Home Assistant announces `Test: Time is up`.

### Manual Test 2: Ignore Invalid Announcements

Call:

```yaml
service: talking_countdown.start
data:
  name: Test
  minutes: 5
  announcements: "10,5,abc,3,3,1"
```

Expected result:

- `10` is ignored because it is longer than the timer.
- `abc` is ignored.
- Duplicate `3` is only announced once.
- Valid announcements occur at 5, 3, and 1 minutes remaining.

### Manual Test 3: Replace Existing Timer

1. Start `Oven` for 30 minutes.
2. Start `Oven` again for 10 minutes.

Expected result:

- The 30-minute timer is cancelled.
- Only the 10-minute timer remains active.

### Manual Test 4: Cancel Timer

1. Start `Laundry` for 10 minutes.
2. Call `talking_countdown.cancel` with `name: Laundry`.

Expected result:

- No remaining announcements occur for `Laundry`.

## Open Questions

- Should active timers survive Home Assistant restart?
- Should the integration create helper entities automatically?
- Should each timer have a generated entity?
- Should announcement units support seconds as well as minutes?
- Should finished announcements repeat until acknowledged?
