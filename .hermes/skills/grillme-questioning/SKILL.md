---
name: grillme-questioning
description: Use when product intent, behavior classification, security implications, or scope are unclear. Ask blocking questions before proceeding with routed work or a harness mutation.
---

# GrillMe Questioning

Rôle: child-time — this skill ships with the generated pack. The father-time counterpart (`father-grilling`) grilled before generation; this skill keeps the discipline during routed work, and it writes into `human-decisions.yml`.

Use this skill when a missing answer would change the harness, the code route, or the safety boundary.

## Rules

- Ask only questions that change the next action.
- Cap at 5 blocking questions per task; each must name the decision it unblocks.
- Ground questions in sources already read.
- If the answer changes preserve/change classification, record the question in `.hermes/control/human-decisions.yml`.
- A blocking question is human-in-the-loop. Only a human answer resolves it.
  Never answer your own question, never proceed on an assumed answer, and never
  record an agent-authored answer in `human-decisions.yml` — a self-answered
  question is fabricated human input. If no human is available, the question
  stays open and the work it blocks stays blocked (fail-closed toward the
  human).

## Before acting

Ask:

- What decision is blocked?
- Which file or behavior is ambiguous?
- What would change depending on the answer?
- Can work continue safely without the answer?

## Output

Return the minimal blocking questions, or proceed with a bounded diff if no blocking question remains.
