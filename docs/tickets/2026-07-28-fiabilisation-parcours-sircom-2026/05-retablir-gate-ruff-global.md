# 05 - Rétablir le gate Ruff global

Statut : `ready-for-agent`

Dépend de : aucun, peut commencer immédiatement.

À construire : l'état versionné du dépôt franchit les deux commandes Ruff
exécutées par la CI, sans changement fonctionnel ni mélange avec les corrections
métier.

## Contexte

Lors de l'audit du 2026-07-28, `ruff check .` réussit mais
`ruff format --check .` retourne un code d'échec. Six fichiers seraient
reformatés, dont cinq fichiers suivis non modifiés et un fichier de la voie
scriptée déjà modifié localement avant l'audit.

La CI exécute le format check avant le lint et les tests. Le dépôt ne dispose
donc pas d'un gate local reproductible tant que cet écart subsiste.

## Critères d'acceptation

- [ ] Tous les fichiers signalés par la version Ruff verrouillée au démarrage
      du ticket sont formatés sans modification de comportement.
- [ ] Les changements locaux préexistants sont préservés et leur intention
      métier n'est ni complétée ni annulée par ce ticket.
- [ ] Aucun fichier généré, donnée locale, zip, log ou backup n'est ajouté.
- [ ] `uv run --frozen --extra test ruff format --check .` retourne zéro.
- [ ] `uv run --frozen --extra test ruff check .` retourne zéro.
- [ ] Les tests ciblés des modules reformatés restent verts si le diff dépasse
      un changement purement syntaxique.
- [ ] Le diff est relu pour confirmer l'absence de changement sémantique.

## Hors périmètre

- Corriger la fusion, les identifiants ou les limites OOXML.
- Refactoriser les modules reformatés.
- Modifier la configuration Ruff ou abaisser les exigences CI.
- Nettoyer le working tree de l'utilisateur.

## Preuve attendue

- sorties des deux commandes Ruff exactes de la CI ;
- `git diff --check` ;
- inspection du diff limitée au format ;
- `git status --short` sans artefact ajouté.

## Sources locales

- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `uv.lock`
- `docs/tickets/2026-07-21-sircom-2026/26-figer-le-format-ruff-global.md`
