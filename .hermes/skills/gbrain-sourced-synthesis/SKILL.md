---
name: gbrain-sourced-synthesis
description: Use when reading code, docs, git history, issues, PRs, CI, or imported context. Produces sourced known/unknown/assumed synthesis instead of raw dumps.
---

# GBrain Sourced Synthesis

Rôle: child-time — this skill ships with the generated pack. The father-time counterpart (`context-brain-reader`) built the bootstrap context brief and is not present here; this skill keeps the same sourced-synthesis discipline alive whenever the child reads sources during routed work.

## Rules

- Separate known, unknown, and assumed facts.
- Tie claims to concrete source paths, commits, issues, PRs, CI records, or human decisions.
- Do not dump raw context.
- Do not invent missing intent.
- Mark contradictions explicitly.

## Before acting

Ask:

- Which source proves this?
- What is still unknown?
- What is only an assumption?
- Which unknown blocks safe generation?

## Output

Return sourced synthesis that can feed `.hermes/control/context-brief.yml`, `.hermes/control/domain-model.yml`, or `.hermes/control/disclosure-map.yml`.
