# 31 - Découper `mapping.py` sans changer le workflow mapping

Statut : `done`

Dépend de : 29B.

À construire : réduire la taille et la responsabilité de
`sircom2026/mapping.py` après verrouillage du contrat public, sans changer le
workflow de mapping, les profils ou l'invalidation aval.

## Énoncé du problème

`mapping.py` porte plusieurs responsabilités : mapping par défaut, validation,
profils, noms CSV et intégration avec les artefacts. Le risque principal d'un
refactor est de changer une règle métier tout en pensant déplacer seulement du
code.

## Solution

Extraire une responsabilité cohérente et testée, par exemple les règles pures
de colonnes et noms CSV, en conservant les entrées publiques du module
historique.

## Critères d'acceptation

- [x] Le contrat du ticket 29B est présent et vert avant déplacement.
- [x] Une responsabilité cohérente est extraite dans un module dédié.
- [x] Les imports publics utilisés par l'API et les tests restent compatibles.
- [x] Le mapping par défaut, la validation, les profils et l'invalidation aval
      gardent le même comportement.
- [x] Les tests mapping, CSV preview et invalidation restent verts.
- [x] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `mapping.py`.

## Hors périmètre

- Modifier les règles de nommage CSV.
- Modifier l'écran mapping.
- Modifier les profils ou le format des artefacts mapping.
- Refactoriser d'autres modules lourds.

## Garde-fous LLM

- Ne pas découper par simple taille de fichier ; découper par responsabilité.
- Ne pas franciser les clés techniques persistées.
- Ne pas ajouter d'abstraction générique si une extraction simple suffit.

## Preuve attendue

- tests du ticket 29B ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Livraison

Découpage réalisé :

- `sircom2026/mapping_rules.py` contient maintenant les règles pures de mapping :
  versions et valeurs de règles, rôles logiques, identifiants des colonnes
  système, filtrage des feuilles utiles, payload structurel, détection des
  rôles par lettre ou en-tête, génération des identifiants de colonne, noms CSV
  courts, nettoyage des noms soumis, colonnes système images et positions
  d'export.
- `sircom2026/mapping.py` conserve le contrat public historique : dataclasses,
  `MappingError`, orchestration API, persistance des brouillons et validations,
  profils, lecture des artefacts, validation métier, invalidation aval et
  enfilement de `fusion_multi_onglets`.
- Les constantes publiques `MAPPING_RULES_VERSION`, `MAPPING_SCHEMA_VERSION`,
  `MAPPING_STATUS_VALUES`, `MAPPING_LOGICAL_ROLES` et `SYSTEM_COLUMN_IDS`
  restent accessibles depuis `sircom2026.mapping`.
- Aucun changement de workflow mapping, de profil, de clé persistée,
  d'invalidation aval, de nom CSV ou de statut de colonne n'a été introduit.

Résultat structurel :

- `sircom2026/mapping.py` passe de 1158 à 1006 lignes.
- `sircom2026/mapping_rules.py` contient 174 lignes dédiées aux règles pures.

Contrôle Loriq :

- Baseline audit-only exécutée avant refactor :
  `/private/tmp/madeinfrance-loriq-ticket31-baseline.json`.
- Résultat Loriq : `finding_count=0`, `status=incomplete`,
  `unknown_count=21`, `task_queue=[]`.
- Limite Loriq observée : la commande a quitté avec le code `3` et
  `audited_project_changed=true`, mais `git status --porcelain` du dépôt audité
  est resté vide juste après l'exécution. Le rapport est conservé comme repère,
  pas comme preuve bloquante.

Preuves exécutées le 2026-07-23 :

- Avant déplacement,
  `uv run --frozen --extra test pytest tests/test_mapping.py tests/test_csv_preview.py tests/test_invalidation.py -q` :
  20 tests passés.
- Après déplacement,
  `uv run --frozen --extra test pytest tests/test_mapping.py tests/test_csv_preview.py tests/test_invalidation.py -q` :
  20 tests passés.
- `uv run --frozen --extra test pytest -q` : 232 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
- `bash scripts/check-accents.sh projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/31-decouper-mapping-sans-changer-workflow.md projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md` :
  OK.
- `git status --short --branch` : changements limités aux deux documents du
  ticket 31, à `sircom2026/mapping.py` et à `sircom2026/mapping_rules.py` avant
  commit.
