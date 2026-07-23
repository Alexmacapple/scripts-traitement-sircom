# Validation Loriq de MadeInFrance

Date : 2026-07-23

Projet validé : `madeinfrance`

SHA validé : `15c2ef6a0ddf9d4ef7618bdb89e4a9c3706827a0`

Loriq utilisé : `bacoco/Loriq@549dec4dd2ba62002ae0b613475b046f3bdbc2af`

## Verdict

Validation positive sur le périmètre ciblé.

- Audit produit Loriq : vert sur clone propre.
- Oracles métier ciblés : 5/5 verts.
- Pytest ciblé sur les mêmes coutures : 5/5 verts.
- Dépôt MadeInFrance réel : non modifié pendant la validation.

## Méthode

La validation a été exécutée sur un clone temporaire Git de MadeInFrance, afin
d'éviter que les artefacts runtime ignorés comme `.sircom2026-data/sircom.sqlite3`
fassent échouer l'invariant read-only de Loriq.

Clone utilisé :

```bash
git clone --local --no-hardlinks \
  /Users/alex/Claude/projets-heberges/madeinfrance \
  /private/tmp/madeinfrance-loriq-validate-15c2ef6
```

Vérification du SHA :

```bash
git rev-parse HEAD
```

Résultat :

```text
15c2ef6a0ddf9d4ef7618bdb89e4a9c3706827a0
```

## Audit produit Loriq

Commande :

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-validate-15c2ef6 \
  --analysis-only
```

Résultat décisif :

```text
status: clean - 0 finding(s), 0 blocked check(s)
harness present: false (temporary copy used: false)
audited project unchanged: yes
```

Interprétation : Loriq ne détecte pas de piste production bloquante sur la
surface déterministe auditable, et l'audit n'a pas muté le clone.

## Oracles métier ciblés

Les oracles ont été exécutés avec le Python du venv MadeInFrance, mais en
pointant explicitement vers le code du clone temporaire.

Commande :

```bash
/Users/alex/Claude/projets-heberges/madeinfrance/.venv/bin/python \
  /private/tmp/madeinfrance_loriq_validation_oracles.py \
  /private/tmp/madeinfrance-loriq-validate-15c2ef6
```

Résultat :

| Oracle | Statut | Preuve |
|---|---:|---|
| `config_limits_public_no_path_leak` | OK | `schema_version=1`, limites `excel/images/disk`, aucun chemin `data_dir`, `sqlite_path` ou `indesign_image_root` dans le payload public. |
| `excel_dimension_guard_rows` | OK | dépassement synthétique `max_rows`, observé `3`, maximum `2`. |
| `image_dimension_guard_pixels` | OK | image synthétique `3x3`, `max_pixels=8`, observé `9`. |
| `disk_guard_low_space` | OK | `SIRCOM_DISK_FREE_LOW`, `free_mb=5119`, `required_mb=5120`, étapes gardées `matching_images` et `package_final`. |
| `csv_indesign_contract` | OK | CSV UTF-16 avec BOM, séparateur virgule, LF, en-têtes `id_dossier`, `imageid`, `@pathimg`, 2 lignes. |

## Pytest ciblé

Commande :

```bash
/Users/alex/Claude/projets-heberges/madeinfrance/.venv/bin/python -m pytest -q \
  tests/test_web_socle.py::WebSocleTest::test_config_limits_do_not_expose_internal_paths \
  tests/test_excel_diagnostic.py::ExcelDiagnosticTest::test_cell_scan_limit_does_not_trust_declared_dimensions_only \
  tests/test_image_upload.py::ImageZipInspectionPipelineTest::test_worker_blocks_images_over_dimension_limits \
  tests/test_worker.py::LocalWorkerTest::test_default_runner_blocks_heavy_jobs_when_disk_is_below_threshold \
  tests/test_csv_contract.py::CsvContractTest::test_writer_and_verifier_match_golden_bytes_and_accept_automatic_quotes
```

Résultat :

```text
5 passed in 0.40s
```

## Ce que cette validation couvre

- Exposition publique des limites de configuration sans fuite de chemins
  internes.
- Refus d'un Excel dont les dimensions dépassent les bornes.
- Refus d'une image dont le nombre de pixels dépasse les bornes.
- Garde disque basse sur les traitements lourds identifiés.
- Contrat CSV InDesign : UTF-16 BOM, virgule, LF, colonnes obligatoires.

## Ce que cette validation ne couvre pas

- Parcours complet upload Excel -> mapping -> images -> rapports -> package.
- Run opérateur Loriq complet `worker -> observe -> judge -> tests -> merge` sur
  le SHA courant.
- Audit RGAA ou accessibilité visuelle.
- Validation sur données réelles Sircom.
- Validation d'un runner `uv` reconstruit dans une copie sans réseau.

## Recommandation

Utiliser ce format comme garde de décision avant les prochains chantiers
risqués : refactor de modules volumineux, contrats publics, flux Excel/images,
package final et changements de worker.

Pour une validation Loriq plus forte, la prochaine étape est de transformer ces
oracles en harnais signé temporaire avec `oracle_runtime.command_prefix` adapté
au venv projet, puis de rejouer un vrai diff de conservation comportementale.
