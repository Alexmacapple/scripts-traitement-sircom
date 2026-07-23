# 29B - Contrat public `mapping.py`

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public du mapping avant
tout nouveau découpage de `sircom2026/mapping.py`.

## Énoncé du problème

`mapping.py` concentre mapping par défaut, brouillons, validation humaine,
profils et noms CSV. Un découpage sans contrat peut casser un détail métier
visible : colonnes exportées, provenance, profils ou invalidation aval.

## Solution

Identifier les fonctions et objets utilisés hors du module, puis ajouter des
tests de contrat sur les comportements qui doivent rester stables.

## Critères d'acceptation

- [ ] Les entrées publiques de mapping utilisées par l'API et le rendu web sont
      listées.
- [ ] Le contrat de mapping par défaut conserve la provenance onglet, lettre,
      nom original, nom CSV et statut exporté.
- [ ] Le contrat de validation conserve l'invalidation aval attendue.
- [ ] Le contrat de profils conserve brouillon, sauvegarde et réapplication.
- [ ] Les cas `id_dossier`, colonnes images, colonnes vides et noms CSV courts
      sont couverts.
- [ ] Aucun refactor de structure n'est réalisé dans ce ticket.
- [ ] `tests.test_mapping`, `tests.test_csv_preview` et
      `tests.test_invalidation` passent.

## Hors périmètre

- Modifier les règles de nommage CSV.
- Modifier l'ergonomie de l'écran mapping.
- Déplacer des fonctions hors de `mapping.py`.

## Garde-fous LLM

- Ne pas transformer le contrat en documentation exhaustive de toutes les
  fonctions privées.
- Verrouiller les comportements observables, pas l'implémentation interne.
- Ne pas changer les clés persistées pour les franciser ; la traduction reste
  dans la couche UI.

## Preuve attendue

- tests de contrat mapping ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
