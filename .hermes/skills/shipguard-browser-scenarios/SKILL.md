---
name: shipguard-browser-scenarios
description: Use when a PoC has UI or browser surfaces. Discovers browser scenarios, marks runtime status honestly, and prevents false green UI claims.
---

# ShipGuard Browser Scenarios

Rôle: child-time — this skill ships with the generated pack. The father-time counterpart (`shipguard-scenario-designer`) designed the initial scenarios; this skill maintains them and their honest runtime status during later work.

Use this skill when HTML, frontend routes, forms, auth flows, or browser-visible behavior exist.

## Rules

- Identify the smallest user path that proves the UI surface matters.
- Record scenarios in `.hermes/control/browser-scenarios.yml`.
- Use `runtime_status: manual_required` unless a real browser run happened.
- Never claim a browser pass from static inspection.
- Prefer Agent Browser only when a local server or static page can actually be opened.

## Before acting

Ask:

- What UI surface exists?
- What user path matters?
- Is there a running server or static file?
- What would a real browser check observe?

## Output

Return browser scenarios with source paths, user paths, criticality, and honest runtime status.
