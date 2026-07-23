# 30 - Découper `image_matching.py` sans changer le comportement

Statut : `done`

Dépend de : 29A.

À construire : réduire la taille et la responsabilité de
`sircom2026/image_matching.py` après verrouillage du contrat public, sans
changer les règles de matching ou les artefacts produits.

## Énoncé du problème

Le module `image_matching.py` reste lourd et mélange règles pures,
orchestration, écriture d'artefacts et traitement des images finales. Cette
taille augmente le coût de revue et la probabilité de corrections accidentelles.

## Solution

Extraire une responsabilité cohérente et testée, en commençant par les règles
pures de sélection ou de qualification des bindings. Le module d'origine doit
conserver les imports publics nécessaires par compatibilité.

## Critères d'acceptation

- [x] Le contrat du ticket 29A est présent et vert avant déplacement.
- [x] Une responsabilité cohérente est extraite dans un module dédié.
- [x] Les imports publics utilisés hors module restent compatibles.
- [x] Aucun statut de binding, code d'erreur, nom final ou artefact ne change.
- [x] Les tests matching, package, rapports et CSV restent verts.
- [x] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `image_matching.py`.

## Hors périmètre

- Améliorer les règles de matching.
- Changer la résolution manuelle.
- Changer la génération des JPG finaux.
- Refactoriser d'autres modules lourds.

## Garde-fous LLM

- Ne déplacer qu'une responsabilité par passe.
- Préserver les noms publics par réexport si nécessaire.
- Ne pas corriger un bug fonctionnel découvert pendant le refactor dans le même
  ticket.

## Preuve attendue

- tests du ticket 29A ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.

## Livraison

Découpage réalisé :

- `sircom2026/image_matching_rules.py` contient maintenant les règles pures de
  matching : inventaire des images racine, colonnes sources d'images, découpage
  des valeurs source, matching exact, matching par nom sans extension, matching
  tolérant, secours par `id_dossier`, suggestions partielles et détection des
  sources automatiques dupliquées.
- `sircom2026/image_matching.py` conserve les constantes et fonctions publiques
  du contrat 29A, l'orchestration worker, la génération du zip final, les
  problèmes structurés, l'exposition des artefacts persistés et les résolutions
  manuelles.
- Les constantes publiques de règles `MATCHING_RULES_VERSION`,
  `MATCHING_SCHEMA_VERSION` et `MATCHABLE_IMAGE_SOURCE_ROLE` restent accessibles
  depuis `sircom2026.image_matching` par import depuis le module de règles.
- Aucun changement de statut, niveau de matching, nom final, code d'erreur,
  nom d'artefact ou format de payload n'a été introduit.

Résultat structurel :

- `sircom2026/image_matching.py` passe de 1452 à 1118 lignes.
- `sircom2026/image_matching_rules.py` contient 351 lignes dédiées aux règles
  pures.

Contrôle Loriq :

- Baseline audit-only exécutée avant refactor :
  `/private/tmp/madeinfrance-loriq-ticket30-baseline.json`.
- Résultat Loriq : `finding_count=0`, `status=incomplete`,
  `unknown_count=22`, `task_queue=[]`.
- Limite Loriq observée : la commande a quitté avec le code `3` et
  `audited_project_changed=true`, mais `git status --porcelain` du dépôt audité
  est resté vide juste après l'exécution. Le rapport est conservé comme repère,
  pas comme preuve bloquante.

Preuves exécutées le 2026-07-23 :

- Avant déplacement,
  `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py -q` :
  19 tests passés.
- Après déplacement, `uv run --frozen --extra test pytest tests/test_image_matching.py -q` :
  13 tests passés.
- Après déplacement,
  `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py -q` :
  19 tests passés.
- Après déplacement,
  `uv run --frozen --extra test pytest tests/test_image_matching.py tests/test_package.py tests/test_reports.py tests/test_csv_preview.py -q` :
  24 tests passés.
- `uv run --frozen --extra test pytest -q` : 232 tests passés, 4 sautés.
- `uv run --frozen --extra test ruff check .` : OK.
- `uv run --frozen --extra test ruff format --check .` : OK.
- `git diff --check` : OK.
- `bash scripts/check-accents.sh projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/30-decouper-image-matching-sans-changer-comportement.md projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md` :
  OK.
- `uv run --frozen --extra test python - <<'PY' ...` : imports publics du
  contrat 29A présents.
