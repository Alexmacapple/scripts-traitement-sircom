---
name: pdd-progressive-disclosure
description: "Use when creating or restructuring docs, code, context packs, or routes. Enforces progressive disclosure: small focused files, summaries, and no giant context dumps."
---

# PDD Progressive Disclosure

Rôle: child-time — this skill ships with the generated pack and applies during routed work in the PoC.

## Rules

- Prefer small, focused files: target ~200 lines (±50), ceiling ~300.
- Keep one concern per file.
- Add a short parent summary when a directory contains multiple child files.
- Preserve source references; do not turn generated summaries into source of truth.
- If `.pdd/` artifacts exist, consume them. Do not rebuild the PDD engine.

## Before acting

Ask:

- What is the smallest file or route needed for this task?
- Which source proves each claim?
- Is this content a source, a summary, or a generated guide?
- Would a future agent need to open this whole file, or can it load a smaller shard?

## Output

Return focused files or a bounded restructuring diff. Do not create reports as deliverables.
