# Inherited rule: shipguard (from the father harness)

Transmitted by the Father Hermes runtime so the child is self-contained. Upstream source of truth: the authoritative repository named below. The father's maintained translation lives at bacoco/Loriq/references/shipguard.md.

---

# ShipGuard / Agent Browser (real rule)

Authoritative source: https://github.com/bacoco/ShipGuard. Agent Browser = the
`agent-browser` Playwright CLI that ShipGuard drives. Built for Claude Code.

## What it actually is

Four AI modules, no test files to write: a Visual E2E Debugger (route discovery,
YAML manifests, real `agent-browser` runs, annotated screenshots traced to
source), a Macro Recorder, a parallel-zone Code Audit writing
`audit-results.json`, and a review dashboard with durable change reports.
`--from-audit` bridges audit → visual via `impacted_ui_routes`.

## The non-negotiable rule

The browser run is real (`agent-browser`/Playwright against a live app). Code audit
narrows; the browser confirms visible reality. Never report a green browser pass
that did not actually run.
