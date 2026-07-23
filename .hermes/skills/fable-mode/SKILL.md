---
name: fable-mode
description: Use when a routed task has many layers — multiple dependent steps, unknowns that could change the approach, debugging where the first theory might be wrong, or any bounded diff that needs verification before handoff. Also use when a task keeps failing or stalling. Sequences this pack's other skills through five gates (scope, evidence, adversarial reasoning, verification, calibrated report); it owns the order, they own their rules.
---

# Fable Mode (five-gate discipline)

Rôle: child-time — this skill ships with the generated pack. The father-time counterpart (`fable-discipline`) applied the same gates while generating this harness; this skill keeps the discipline alive during routed work.

It is a method skill and an ordering layer: it decides WHEN each discipline in this pack applies, and what counts as a gate passed. It owns no rule that another skill here already owns — where a gate touches another skill's ground it defers to that skill, and if wording ever seems to disagree, the owner skill wins.

## Ownership map

| Ground | Owner |
|---|---|
| Objective lock, scope drift, no fake verification | `pdg-mission-guard` |
| Blocking questions, human decisions | `grillme-questioning` → `.hermes/control/human-decisions.yml` |
| Sourced evidence (known/unknown/assumed) | `gbrain-sourced-synthesis` |
| Recall/capture of past learnings | `hermes-memory` |
| Change-side red/green proof and non-tautological regression tests | `tdd-red-green` |
| Browser/UI honesty | `shipguard-browser-scenarios` (when shipped) |
| Small focused files and context | `pdd-progressive-disclosure` |
| The loop itself: gate order, pass criteria, smells | this skill |

## The five gates, in order

A gate must pass before the next one opens. When a task stalls or a result surprises you, name which gate you are at and re-run it. A hard task is anything where the first idea might be wrong; for a one-file edit or a simple lookup, skip the gates and just do the work.

1. **Scope before work.** State what done looks like in one or two sentences: what artifact exists at the end and which check proves it — answering `pdg-mission-guard`'s four questions is this gate's pass condition. Name the one to three load-bearing unknowns. If an ambiguity changes the diff you would produce, it is a `grillme-questioning` blocking question; otherwise state the chosen default in one line and proceed. Close the gate with a two-minute premortem: assume the diff has already failed; name the likeliest concrete cause; add a check for it.
2. **Evidence before reasoning.** Open the real files before designing; training memory is only a hypothesis generator. `gbrain-sourced-synthesis` owns how evidence is sourced; `hermes-memory` recalls what past runs learned. For behavior changes and bug fixes, `tdd-red-green` owns the red-capable seam test before the fix. This gate adds the ordering: attack the load-bearing unknowns first, with the cheapest probe, and prefer a thin end-to-end pass over a complete first stage. Before running any probe or test, state the expected result — a mismatch forces re-diagnosis, never a rationalization.
3. **Reason adversarially.** Before committing to a diff, switch roles and try to kill it: what input, state, or reading makes it wrong? Actually test that case. Steelman the existing code before changing it — the behavior contract's preserve entries usually name the reason it is the way it is. If `tdd-red-green` cannot find a correct seam, record that instead of writing a false-confidence test. Two failed attempts at the same fix mean the diagnosis is wrong: stop patching, find the assumption underneath both attempts and test it directly. When reviewing, finding nothing wrong is a legitimate result.
4. **Verify before declaring done.** Verify at the layer of the claim, with evidence you did not generate: re-open the written file, run the route's tests, the red/green proof when one was created, and sealed oracles, diff before against after, sample the tails and not just the middle. The no-fake-verification, red/green and browser-honesty rules live with their owners (`pdg-mission-guard`, `tdd-red-green`, `shipguard-browser-scenarios`); this gate is the moment they are enforced. Treat a surprisingly clean result as suspect until you can explain why it is real. Declare done when the diff definitely improves the PoC even if imperfect — record leftover polish as nits rather than blocking on it.
5. **Report calibrated.** Lead with the answer. Separate verified from assumed, out loud, with specifics: paths, commands run, output observed. Report observations, not intentions — if something failed or was skipped, say so. Never state as fact what this session did not verify; tag every unchecked claim with a literal `unverified` marker.

When the loop closes and a durable lesson exists, capture it with `hermes-memory` — a method that never updates itself repeats its failures.

## Smells that mean a gate got skipped

- Building without having opened the real file, data, or API response it depends on (Gate 2).
- "Should work" said or thought about something testable right now (Gate 4).
- Attempt three of the same fix (Gate 3).
- Three actions in a row from the original plan with no check against intermediate results (Gate 3).
- About to report done with intention as the only evidence (Gate 4).
- An anomaly outside the current scope was noticed — and built on instead of surfaced (Gate 3: stop the line; never pass a defect downstream).

Any one of these: stop, go back to that gate.

## Before acting

Ask:

- Is this task hard enough to need the gates at all?
- Which gate is the task at, and did the previous one actually pass?
- What is the cheapest probe of the biggest remaining unknown?
