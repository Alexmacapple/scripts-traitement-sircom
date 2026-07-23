# 29A - Contrat public `image_matching.py`

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : documenter et verrouiller le contrat public du matching images
avant tout nouveau découpage de `sircom2026/image_matching.py`.

## Énoncé du problème

`image_matching.py` reste volumineux et porte à la fois règles de matching,
résolutions manuelles, génération d'artefacts et orchestration worker. Un
refactor sans contrat peut passer les tests généraux tout en modifiant une règle
implicite importante pour le package final.

## Solution

Créer un contrat court des fonctions, erreurs, statuts et artefacts publics à
préserver. Ajouter ou renforcer les tests de contrat sur les cas critiques avant
de déplacer du code.

## Critères d'acceptation

- [ ] Les entrées publiques de matching utilisées par l'API, le worker, les
      rapports et le package sont listées.
- [ ] Les statuts de binding images et leurs libellés attendus sont listés.
- [ ] Les cas exact, tolérant, ambigu, source dupliquée, image manquante et
      collision de nom final sont couverts par tests.
- [ ] Les exceptions métier et codes d'erreur attendus sont couverts.
- [ ] Aucun refactor de structure n'est réalisé dans ce ticket.
- [ ] `tests.test_image_matching`, `tests.test_package` et `tests.test_reports`
      passent.

## Hors périmètre

- Déplacer des fonctions hors de `image_matching.py`.
- Changer les règles de matching.
- Changer les noms finaux `dossier-{id-normalise}.jpg`.

## Garde-fous LLM

- Ce ticket prépare le refactor, il ne le fait pas.
- Si une règle semble incorrecte, la noter comme dette séparée au lieu de la
  corriger.
- Les clés techniques persistées peuvent rester en anglais côté API et base ;
  les libellés visibles restent en français.

## Preuve attendue

- tests de contrat matching images ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
