---
name: project-architecture
description: "Use when working on source entrypoints and behavior-contract routed code-hardening work; read the routed context and behavior-contract first."
---

# Project Architecture

Single source of truth for this skill; the `.claude/` and `.agents/` copies are thin
generated adapters that point here.

## This project (runtime-scaffolded — the father flow replaces this with the real architecture)

- Objective: preserve the historical Sircom 2025 processing chain and InDesign export contract while hardening the Sircom 2026 web application Excel fusion, image matching, CSV export, package generation and UI workflow.
- Code center: sircom2026/app.py, sircom2026/static/app.js
- Primary doc: README.md

The mechanical runtime can only scaffold these pointers. The father flow
(modules, data flow, contracts, invariants) is expected to rewrite this section
with the PoC's real architecture.

Use this vocabulary when describing the project:
- module: a coherent behavior behind an interface;
- interface: everything callers and tests must know, including invariants and
  error modes;
- seam: where behavior can be observed or varied without reaching into internals;
- adapter: a concrete implementation at a seam;
- depth: how much useful behavior sits behind a small interface.

Tests and `tdd-red-green` proofs should cross the same seam a user or caller
would use. If the only testable surface is private internals, report the design
gap instead of writing a false-confidence test.

Before acting on a routed task:
- read the routed context and `.hermes/control/context-brief.yml`;
- Preserve ONLY what `.hermes/control/behavior-contract.yml:preserve` lists with `status: confirmed`.
- Change ONLY what `.hermes/control/behavior-contract.yml:change` lists with `status: confirmed`.
- Entries with `status: proposed` are father-derived from an explicit source but await human confirmation — treat them as unclassified until a human confirms.
- If a behavior is unclassified or ambiguous, STOP and add a concrete question to `.hermes/control/human-decisions.yml`. Do not guess; do not preserve "observed behavior" by default.

## Inherited disciplines — preserve them when you CREATE docs or code

The full rules are transmitted in `.hermes/inherited/*.md`; apply them, do not just store them:
- Progressive disclosure (PDD): shard large docs/code into focused, separately-loadable files; keep each ~200 lines (±50, ceiling ~300); one concern per file.
- Sourced synthesis (GBrain): tie every claim to a source; name what is unknown; no raw dumps.
- Mission discipline (PDG): keep the objective locked; expose deviations; no fake verification.
- Real confirmation (ShipGuard): never report a green browser/test pass that did not actually run.
- Grill first (GrillMe / Grill With Docs): ask the blocking questions before generating.
- Consume, don't rebuild (PDD/PDD-IAR): read `.pdd/` artifacts if present; do not re-implement engines.
