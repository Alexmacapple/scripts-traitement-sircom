---
name: tdd-red-green
description: Use when a routed child task changes behavior, fixes a bug, or needs a regression proof — write one red-capable test at a confirmed seam before the fix, then make it green without self-confirming the contract.
---

# TDD Red/Green

Rôle: child-time — this skill ships with the generated pack. Father-time
counterpart: `oracle-designer` seals confirmed behavior oracles; this skill only
creates candidate proof during routed work.

## Purpose

Turn a requested change into evidence. For a defect or behavior change, produce
one small test or probe that can fail on the current problem, then make the
minimal diff that turns it green.

This is change-side evidence. It is not human confirmation, not a sealed oracle,
and never an approval signal.

## When It Applies

Use this when a route asks you to:

- fix a bug or regression;
- add or alter behavior named by a confirmed `change` id;
- harden code in a way that needs a user-visible or API-visible proof;
- explain that no correct test seam exists.

For pure prose edits, mechanical renames, or tasks whose route already supplies a
sealed oracle that directly covers the change, keep the gate light and say why no
new red/green test is needed.

## Loop

1. Name the seam: the public interface where behavior is observable. Use
   `.hermes/control/domain-model.yml`, route context and existing tests to choose
   the seam. If the seam is ambiguous and the test shape would change, ask via
   `grillme-questioning`.
2. Write the smallest red-capable test or probe. It must assert the exact defect
   or requested behavior, not just "does not crash".
3. Run it before the fix and record the red result. If it cannot go red on the
   current problem, delete or rewrite it before touching implementation.
4. Make the minimum implementation diff. Do not add speculative behavior for
   imagined future tests.
5. Run the new test/probe green, then run the route's existing tests and sealed
   oracles. Preserve-side proofs still own regression safety.
6. Report the test command, the red result, the green result and whether the new
   proof should be proposed to the human as a future sealed `change` oracle. A
   proof born from a human correction or a vetoed/blocked diff is always
   proposed: that is how a one-off correction becomes a permanent oracle instead
   of a journal line (counterpart: `hermes-memory` correction graduation).

## Good Proof

- Tests behavior through the seam, not private implementation.
- Uses expected values from a source independent of the implementation: a known
  literal, fixture, spec example, user symptom, or confirmed contract entry.
- Covers one vertical slice; one seam, one failing signal, one fix.
- Can be run unattended by the agent.

## Hard Bugs

For a bug that is not immediately reproducible, the first deliverable is the
feedback loop, not the theory. Build the tightest red-capable command you can:
a focused test, CLI probe, HTTP request, browser script, captured-trace replay,
or minimal throwaway harness. It must drive the user's symptom, be deterministic
enough to debug, and run without human clicks. If no such loop can be built,
report what artifact or access is missing before hypothesizing.

## If No Correct Seam Exists

Stop and say so. Record what would need to change architecturally before the bug
can be locked down. Do not write a shallow test that gives false confidence.

## Forbidden

No tautological assertions. No tests that only mirror constants from the code
under test. No implementation-coupled tests unless no public seam exists and the
limitation is reported. No `status: confirmed` edits. No oracle edits by the
child. No `approve`, readiness score, or validation-of-validation.
