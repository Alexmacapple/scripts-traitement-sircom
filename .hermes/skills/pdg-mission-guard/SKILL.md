---
name: pdg-mission-guard
description: Use when a task needs objective lock, deviation handling, or real verification discipline. Prevents scope drift, fake verification, validation-of-validation, and vague mission changes.
---

# PDG Mission Guard

Rôle: child-time — this skill ships with the generated pack and applies during routed work in the PoC.

Use this skill before changing scope, tools, behavior classifications, or success criteria.

## Rules

- Treat the task as a mission under constraints, not as permission to broaden the project.
- Keep `.hermes/profile.yml:project.objective` locked unless a human explicitly changes it.
- If work drifts from the objective, stop and record a concrete question in `.hermes/control/human-decisions.yml`.
- Never claim verification unless the stated check actually ran.
- Never create an agent, report, or review whose only purpose is to validate another agent, report, or review.

## Before acting

Ask:

- What exact objective is being served?
- Which constraint would this change affect?
- Is this preserve, change, or human decision?
- What real command, diff, browser run, or human decision would prove completion?

## Output

Return a bounded diff or a blocker tied to `.hermes/control/human-decisions.yml`.
