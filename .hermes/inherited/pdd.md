# Inherited rule: pdd (from the father harness)

Transmitted by the Father Hermes runtime so the child is self-contained. Upstream source of truth: the authoritative repository named below. The father's maintained translation lives at bacoco/Loriq/references/pdd.md.

---

# PDD — Progressive Disclosure Documentation (real rule)

Authoritative source: https://github.com/bacoco/progressive-disclosure-documentation
(README + the `.pdd/` artifacts it produces).

Companion consumer — PDD-IAR ("Investigative Autoregressive Retrieval"), consumer
layer for `.pdd/` artifacts: https://github.com/bacoco/progressive-disclosure-iar — reads `.pdd/`
artifacts, verifies the disclosure contract, searches mapped sources, and returns
an answerability state. Generated docs are orientation only, never source proof.

## What it actually is

A documentation engine — not a chatbot. "A chatbot can consume PDD artifacts, but
the engine must work on its own." Relationship:

```text
PDG frames the work -> PDD produces artifacts -> PDD Chat consumes artifacts
```

If `.pdd/` artifacts exist in a project, consume them as context; never rebuild
the PDD engine, and never turn generated summaries into the source of truth.
