# 26 - Figer le format Ruff global

Statut : `ready-for-agent`

Dépend de : 25.

À construire : rendre `ruff format --check .` exploitable comme garde de style
global, avec une passe mécanique sans changement du comportement métier.

## Énoncé du problème

Le ticket 25 a rendu `ruff check .` vert. Il reste une dette de formatage :
`ruff format --check .` signale encore de nombreux fichiers Python à reformater.

Cette dette n'est pas un bug fonctionnel, mais elle crée du bruit pour les
revues futures. Tant que le format n'est pas figé, un agent peut mélanger une
correction métier et un grand diff de style.

## Solution

Appliquer le format Ruff sur le dépôt en une passe mécanique isolée, puis
ajouter le contrôle `ruff format --check .` à la CI.

## Critères d'acceptation

- [ ] `uv run --frozen --extra test ruff format .` a été exécuté seul ou dans un
      commit dédié au formatage.
- [ ] `uv run --frozen --extra test ruff format --check .` passe.
- [ ] `uv run --frozen --extra test ruff check .` passe.
- [ ] `uv run --frozen --extra test pytest -q` passe.
- [ ] Le test navigateur Playwright passe si un fichier consommé par
      l'interface est touché par le formatage.
- [ ] La CI exécute `ruff format --check .`.

## Hors périmètre

- Modifier le comportement métier.
- Renommer des fonctions, routes, clés JSON ou libellés UI.
- Ajouter des exclusions Ruff pour éviter le formatage.
- Mélanger une correction fonctionnelle avec le formatage.

## Garde-fous LLM

- Le ticket est un changement mécanique. Ne pas corriger de bug découvert en
  passant.
- Si un fichier formaté révèle un comportement douteux, ouvrir un ticket séparé
  ou le noter en rapport final.
- Ne pas toucher aux assets DSFR, polices, fichiers minifiés ou artefacts
  générés.

## Preuve attendue

- `uv run --frozen --extra test ruff format --check .`
- `uv run --frozen --extra test ruff check .`
- `uv run --frozen --extra test pytest -q`
- `git diff --check`
