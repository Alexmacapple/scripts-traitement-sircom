# 28 - Ajouter un seuil de couverture en CI

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : ajouter une mesure de couverture Python en CI avec un seuil
initial conservateur, pour empêcher les régressions silencieuses de tests.

## Énoncé du problème

La suite de tests est riche et passe en CI, mais aucun seuil de couverture
n'empêche une baisse progressive de la surface testée. Le dépôt peut donc
garder une CI verte tout en perdant du filet de sécurité.

## Solution

Ajouter l'outillage de couverture au groupe de dépendances de test, mesurer la
couverture actuelle de `sircom2026`, puis fixer un seuil initial non agressif.
Le seuil doit protéger contre les régressions sans transformer ce ticket en
campagne de tests.

## Critères d'acceptation

- [ ] La dépendance de couverture est épinglée dans les dépendances de test.
- [ ] La CI exécute la suite avec couverture sur le package `sircom2026`.
- [ ] Le seuil initial est documenté dans `pyproject.toml` ou dans la commande
      CI.
- [ ] Le seuil choisi est justifié par la mesure actuelle et laisse une marge
      faible, par exemple un arrondi inférieur de la couverture mesurée.
- [ ] `uv run --frozen --extra test pytest -q` passe.
- [ ] La commande de couverture passe localement.

## Hors périmètre

- Monter artificiellement la couverture en écrivant des tests pauvres.
- Imposer un seuil sur les scripts historiques `scripts-2025/` dans cette
  première passe.
- Refactoriser du code pour améliorer la couverture.

## Garde-fous LLM

- Ne pas inventer un seuil arbitraire élevé.
- Ne pas exclure massivement des fichiers pour embellir le pourcentage.
- Si la couverture actuelle est plus basse que prévu, livrer un seuil bas mais
  réel, puis ouvrir des tickets de renforcement ciblés.

## Preuve attendue

- commande de couverture avec seuil ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
