# Inherited rule: pdg (from the father harness)

Transmitted by the Father Hermes runtime so the child is self-contained. Upstream source of truth: the authoritative repository named below. The father's maintained translation lives at bacoco/Loriq/references/pdg.md.

---

# PDG — Progressive Disclosure Guard (real rule)

Authoritative source: https://github.com/bacoco/progressive-disclosure-guard.
Stable skill slug / repo name: `progressive-disclosure-guard`.

## What it actually is

"A Marc Aurelus mission harness for AI agents — do not prompt the agent, brief the
mission." ("Marc Aurelus" is the upstream project's own spelling, verified verbatim
against its README; it refers to Marcus Aurelius.) A small guardrail for Claude
Code / Codex that forces progressive disclosure: the agent must earn the next layer
of detail instead of jumping to one giant plan, one giant file, one vague refactor,
or one fake verification. Requests are objectives under constraints, not rails.

For risky work the agent must: identify the real objective; respect explicit
constraints; distinguish known / unknown / assumed; choose the best method within
the framework; expose deviations before acting; verify limits before answering.

Mission Brief is the interface: Mission, Objective Lock, Constraints, Success
Criteria, Progressive Disclosure Gates, Deviation Protocol, Verification Protocol,
Deliverable.

Guards against: premature architecture, giant plans, giant files, fake
verification, silent scope drift, source-of-truth bypass, generated-output
mismatch, multi-agent busywork, parallel engines/stores/routers/workflows.
