# CyberFlow — iPhone-first client direction

Status: product direction for WB-0035 exploration
Date: 2026-08-23

## Decision

CyberFlow is **iPhone-first**.

Android is explicitly out of the MVP scope. It may be reconsidered later, but it must not influence the first client architecture, UX, integration priorities, or release sequencing.

The first deployment hostname remains:

```text
tasks.cyberdjs.org
```

## Client priority

1. iPhone
2. responsive web/PWA as operational fallback
3. macOS integration where useful
4. Android only as a later optional target

## iPhone-first capabilities

The MVP/client design should prioritize native iOS interaction surfaces rather than reproducing a generic web task manager:

- Share Sheet capture from Safari, Photos, Mail and other apps;
- Shortcuts / App Intents for fast capture and task actions;
- Siri-triggered capture where technically appropriate;
- Home Screen and Lock Screen widgets for NOW/TODAY state;
- notifications with low-friction complete/snooze/defer actions;
- deep links directly to a task, project, capture or focus session;
- Focus Mode awareness where exposed safely by iOS APIs;
- camera/photo/screenshot capture as an input to the inbox;
- voice capture with later structured triage;
- offline-tolerant capture queue with later synchronization;
- Face ID / device security for local sensitive state where needed.

## Product principle

The iPhone client should not try to expose the entire task database.

Its primary job is to reduce cognitive switching cost through a small set of interaction modes:

```text
CAPTURE
NOW
RESUME
PLAN
CHECK-IN
```

The backend may remain Vikunja during the MVP. CyberFlow's durable product value should be the attention/context layer and its iPhone interaction model, not a fork of Vikunja's generic task UI.

## Suggested architecture

```text
iPhone client / PWA fallback
        |
CyberFlow capability API
        |
CyberCore orchestration/context
        |
Vikunja API
        |
Vikunja task/project store
```

This keeps the client independent of Vikunja-specific API details and allows the task backend to be replaced later without redesigning the iPhone UX.

## MVP release order

### v0 — backend proving ground

- Vikunja on `tasks.cyberdjs.org`;
- minimal INBOX / TODAY / THIS WEEK / LATER workflow;
- CyberCore API integration proof;
- no native client required yet.

### v0.1 — iPhone capture companion

- sign-in;
- fast text/voice capture;
- Share Sheet;
- TODAY/NOW view;
- complete/defer;
- deep links.

### v0.2 — context resurrection

- resume last task/context;
- WHY / NEXT / BLOCKED BY / LAST CONTEXT;
- focus-session check-ins;
- lightweight widgets/notifications.

### Later

- richer project management;
- team handoff;
- macOS companion;
- optional Android client only if justified by real demand.
