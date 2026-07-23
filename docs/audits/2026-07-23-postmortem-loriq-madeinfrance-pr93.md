# Post-mortem Loriq x MadeInFrance - validation PR #93

Date : 2026-07-23

Projet cible : `madeinfrance`

Loriq testé : `bacoco/Loriq@549dec4`

MadeInFrance testé : `15c2ef6`

## Résumé court

La PR #93 fonctionne sur le point critique : les oracles `python-stdout`
peuvent déclarer un runner projet via `oracle_runtime.command_prefix`, ce
runner est couvert par la signature, et les échecs d'observe ne sont plus
opaques.

Le blocage initial n'est plus "Loriq rejoue hors environnement projet". Le
nouveau blocage réel est plus précis : le runner choisi doit être compatible
avec un replay offline dans la copie d'observation. Avec
`uv run --frozen --extra test python -c`, `uv` a tenté de reconstruire
l'environnement et a échoué sans accès PyPI. Avec un runner résolu sur `PATH`
vers le venv projet, l'observer passe.

## État de départ

### Loriq

- Checkout local mis à jour par `git pull --ff-only`.
- Passage de `f8618a3` à `549dec4`.
- `HEAD = origin/main = 549dec4`.
- Aucun commit réalisé dans Loriq.
- Remote push toujours désactivé côté Loriq : `DISABLED-bacoco-push`.
- Deux modifications locales préexistantes conservées intactes :
  - `docs/specs/2026-07-22-couche-amont-ia-spec.md` ;
  - `operator/DOCTRINE.md`.

### MadeInFrance

- `HEAD = origin/main = 15c2ef6`.
- Worktree propre avant et après les tests sur le dépôt réel.

## Audit produit Loriq

Commande lancée sur le checkout réel :

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /Users/alex/Claude/projets-heberges/madeinfrance \
  --analysis-only
```

Résultat :

- rapport : `status: clean`, `0 finding`, `0 blocked` ;
- exit non-zéro, car l'invariant read-only a détecté
  `audited_project_changed: true` ;
- cause locale observée : `.sircom2026-data/sircom.sqlite3` a changé pendant
  la fenêtre d'audit ;
- `git status` de MadeInFrance restait propre.

Interprétation : le code n'a pas été modifié ; le scanner de mutation Loriq voit
aussi les artefacts runtime ignorés. Sur un dépôt applicatif local avec un
SQLite vivant, l'audit doit se faire sur une copie propre ou avec le runtime
arrêté.

Relance sur clone propre :

```bash
git clone --local --no-hardlinks \
  /Users/alex/Claude/projets-heberges/madeinfrance \
  /private/tmp/madeinfrance-loriq-audit-15c2ef6

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-audit-15c2ef6 \
  --analysis-only
```

Résultat :

- `status: clean` ;
- `finding_count: 0` ;
- `blocked: []` ;
- `harness.present: false` ;
- `temporary_copy_used: false` ;
- `audited_project_changed: false`.

## Validation `oracle_runtime`

Le harnais temporaire réutilisé était :

```text
/private/tmp/madeinfrance-loriq-feature.4uYgyl/madeinfrance
```

Oracle concerné :

```yaml
behavior_id: change-config-limits-schema-version
kind: change
command: '... TestClient(create_app(settings)).get("/api/config/limits") ...'
expected_stdout: "1 True False"
must_fail_before: true
```

L'oracle importe `fastapi.testclient` et `sircom2026`. C'est donc exactement le
cas qui avait cassé auparavant : un `python-stdout` rejoué hors environnement
projet.

### Preuve de signature fail-closed

Ajout initial :

```yaml
oracle_runtime:
  command_prefix: [uv, run, --frozen, --extra, test, python, -c]
```

Validation lancée :

```bash
.venv/bin/python runtime/validate.py \
  --poc-repo /private/tmp/madeinfrance-loriq-feature.4uYgyl/madeinfrance \
  --require-signed-confirmation
```

Résultat attendu :

```text
confirmed entry change-config-limits-schema-version:
confirmation signature does not verify for principal alex-human-go-2026-07-23
```

Interprétation : `oracle_runtime.command_prefix` est bien couvert par le sceau.
Changer le runner impose une nouvelle confirmation signée.

Après cérémonie signée, le pack repasse `status: passed`.

## Résultat du runner `uv`

Run opérateur avec Loriq `549dec4` :

```bash
env PYTHONPATH=/Users/alex/Claude/projets-heberges/Loriq/operator \
  .venv/bin/python -m hoperator.main run \
  --config /private/tmp/madeinfrance-loriq-feature.4uYgyl/operator/operator.yml \
  --root /private/tmp/madeinfrance-loriq-feature.4uYgyl/operator \
  --max-tasks 1
```

Résumé terminal produit par Loriq :

```text
task: config-limits-schema-version-3 | status: failed | phase: observe
cause: oracle-runtime-error | report: /private/tmp/madeinfrance-loriq-feature.4uYgyl/operator/queue/failed/config-limits-schema-version-3/report.json
next: read the triage evidence in the report; for observe failures, open the observation.json diagnostics (stderr, failure_kind)
```

Ce résumé est déjà un progrès produit important : le run n'est plus silencieux.

Dans `observation.json`, Loriq expose :

- `failure_kind: probe_runtime_error` ;
- `exit_code: 1` ;
- `executable: /opt/homebrew/bin/uv` ;
- `runner: [uv, run, --frozen, --extra, test, python, -c]` ;
- `cwd`: copie temporaire d'observation ;
- `stderr` borné et lisible.

Cause précise :

```text
Failed to resolve requirements from build-system.requires
No solution found when resolving: setuptools>=69
Failed to fetch: https://pypi.org/simple/setuptools/
dns error
```

Interprétation : la PR #93 a bien fait rejouer l'oracle dans le runner déclaré.
Le blocage restant vient du choix du runner : `uv` tente de reconstruire
l'environnement dans la copie d'observation et échoue sans réseau/cache.

## Validation positive avec runner PATH offline

Runner local créé hors pack :

```sh
madeinfrance-project-python -c
```

Il pointe vers le venv MadeInFrance déjà installé. L'oracle reste portable côté
pack, car il déclare seulement un nom d'outil résolu sur `PATH` :

```yaml
oracle_runtime:
  command_prefix: [madeinfrance-project-python, -c]
```

Le changement de runner a de nouveau invalidé la signature existante. Après
nouvelle cérémonie signée, le pack repasse `status: passed`.

Replay direct de l'observer :

```bash
env PATH=/private/tmp/madeinfrance-loriq-feature.4uYgyl/bin:$PATH \
  PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python runtime/diff_observer.py \
  --poc-repo /private/tmp/madeinfrance-loriq-feature.4uYgyl/madeinfrance \
  --route feature-config-limits-schema-version-route \
  --baseline-ref 31d2cfd08493222f77fedc2d2db62a54b152525c \
  --task "Implement only the confirmed feature behavior from docs/specs/2026-07-23-config-limits-schema-version-feature.md: update GET /api/config/limits in sircom2026/web_routes.py so the JSON response includes root schema_version equal to 1 while preserving the existing public limits object and continuing to hide internal paths such as data_dir and sqlite_path." \
  --require-confirmed change-config-limits-schema-version \
  --oracles \
  --no-events
```

Résultat :

- `status: passed` ;
- `sandboxed: true` ;
- patch limité à `sircom2026/web_routes.py` ;
- baseline rouge attendu :
  - `stdout: "None True False"` ;
  - `failure_kind: assertion_mismatch` ;
  - `passed_before: false` ;
- patch vert :
  - `stdout: "1 True False"` ;
  - `passed: true`.

## Verdict

PR #93 validée sur le point produit important.

Ce qui est prouvé :

- un oracle `python-stdout` peut déclarer un runner projet ;
- le runner est utilisé par l'observer ;
- le runner est couvert par la signature ;
- changer le runner invalide la confirmation existante ;
- les erreurs de probe sont typées et exploitables ;
- le résumé terminal donne phase, cause, report et prochaine action ;
- MadeInFrance passe l'observer avec un runner projet offline-compatible.

Ce qui n'est pas prouvé :

- cycle complet `worker -> observe -> judge -> tests -> merge` avec ce runner :
  le run opérateur suivant a échoué avant observe sur un problème worker Codex
  local `Operation not permitted`.

Ce qui est un résiduel réel :

- `uv run --frozen --extra test python -c` est conceptuellement bon, mais fragile
  si la copie d'observation doit créer son environnement sans réseau/cache ;
- `product_audit.py` peut signaler une mutation si des artefacts ignorés vivants
  changent pendant l'audit, même avec un Git propre.

## Recommandations

Ne pas assouplir observe, les signatures ou les cérémonies. Elles ont fait le
bon travail.

Amélioration utile côté Loriq :

- ajouter une documentation "oracle runner cookbook" :
  - `uv` avec cache/env prêt ;
  - venv local via shim `PATH` ;
  - réseau interdit ;
  - dépendance absente ;
  - runner introuvable ;
  - distinction défaut projet / défaut runner ;
- préciser pour `product_audit.py` que les artefacts runtime ignorés mais
  vivants peuvent casser l'invariant read-only, et recommander clone propre ou
  arrêt du runtime.

## Commandes décisives

```bash
git pull --ff-only
git rev-parse HEAD origin/main
git status --short --branch

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /Users/alex/Claude/projets-heberges/madeinfrance \
  --analysis-only

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-audit-15c2ef6 \
  --analysis-only

.venv/bin/python runtime/validate.py \
  --poc-repo /private/tmp/madeinfrance-loriq-feature.4uYgyl/madeinfrance \
  --require-signed-confirmation

env PYTHONPATH=/Users/alex/Claude/projets-heberges/Loriq/operator \
  .venv/bin/python -m hoperator.main run \
  --config /private/tmp/madeinfrance-loriq-feature.4uYgyl/operator/operator.yml \
  --root /private/tmp/madeinfrance-loriq-feature.4uYgyl/operator \
  --max-tasks 1

env PATH=/private/tmp/madeinfrance-loriq-feature.4uYgyl/bin:$PATH \
  PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python runtime/diff_observer.py \
  --poc-repo /private/tmp/madeinfrance-loriq-feature.4uYgyl/madeinfrance \
  --route feature-config-limits-schema-version-route \
  --baseline-ref 31d2cfd08493222f77fedc2d2db62a54b152525c \
  --require-confirmed change-config-limits-schema-version \
  --oracles \
  --no-events
```

## État final

- Loriq réel : à jour sur `549dec4`, sans commit local ajouté.
- MadeInFrance réel : propre, `HEAD = origin/main = 15c2ef6`.
- Validations complémentaires réalisées dans `/private/tmp`.
- Les commits de harnais sont temporaires et non destinés à `bacoco/Loriq`.
