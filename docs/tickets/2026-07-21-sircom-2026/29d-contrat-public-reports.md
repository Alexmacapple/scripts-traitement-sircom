# 29D - Contrat public `reports.py`

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public de génération des
rapports avant tout nouveau découpage de `sircom2026/reports.py`.

## Énoncé du problème

`reports.py` porte à la fois collecte de données, rendu du rapport métier,
rendu du rapport technique et écriture d'artefacts. Un refactor sans contrat
peut changer le contenu attendu du package final ou réintroduire des valeurs
sensibles dans le rapport technique.

## Solution

Verrouiller les noms d'artefacts, sections du rapport métier, champs techniques
principaux et règles d'absence de données sensibles.

## Critères d'acceptation

- [ ] Les artefacts `rapport-metier.md` et `rapport-technique.json` restent
      nommés ainsi.
- [ ] Les sections fixes du rapport métier restent listées et testées.
- [ ] Le rapport technique conserve les compteurs, durées, tailles, codes
      erreur et traces anonymisées attendues.
- [ ] Les scénarios avec images, sans images et avec alertes ouvertes sont
      couverts.
- [ ] L'absence de valeurs métier sensibles dans le rapport technique est
      testée.
- [ ] Aucun refactor de structure n'est réalisé dans ce ticket.
- [ ] `tests.test_reports`, `tests.test_package` et `tests.test_csv_preview`
      passent.

## Hors périmètre

- Changer le format métier des rapports.
- Changer le package final.
- Déplacer les fonctions hors de `reports.py`.

## Garde-fous LLM

- Ne pas embellir les rapports dans ce ticket.
- Ne pas ajouter de nouveaux champs techniques sans besoin de contrat.
- Si un libellé métier est incohérent, le noter séparément au lieu de le
  corriger.

## Preuve attendue

- tests de contrat rapports ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
