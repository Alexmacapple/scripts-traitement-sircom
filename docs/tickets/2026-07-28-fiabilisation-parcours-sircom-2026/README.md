# Tickets - Fiabilisation des parcours Sircom 2026

Date : 2026-07-28

Parent :
[spec de fiabilisation](../../specs/2026-07-28-fiabilisation-parcours-sircom-2026.md).

Mode de publication : dossier Markdown local avec un fichier par ticket, selon
la destination explicitement demandée par l'utilisateur.

## Frontier

Frontier agent initiale :

- 05 - Rétablir le gate Ruff global.

Frontier humaine initiale :

- 06 - Décider le contrat des champs InDesign 2026.

Ordre agent après 05 :

1. 02 - Préserver les identifiants textuels dans les deux parcours ;
2. 01 - Fusionner les onglets dans la voie scriptée, après 02 ;
3. 03 et 04 peuvent avancer indépendamment après 05.

Après 01 à 06 :

- checkpoint : comparer les sorties synthétiques post-tickets à l'oracle 06 ;
- 06A - adapter et tester les exports, uniquement si ce checkpoint l'active ;
- 07 - recetter les deux parcours, après 06A s'il est activé.

## Tickets

| N | Statut | Ticket | Dépend de |
|---|---|---|---|
| 01 | `blocked` | [Fusionner les onglets dans la voie scriptée](01-fusionner-onglets-voie-scriptee.md) | 02 |
| 02 | `blocked` | [Préserver les identifiants textuels dans les deux parcours](02-preserver-identifiants-textuels.md) | 05 |
| 03 | `blocked` | [Borner les archives OOXML et refuser les lignes métier masquées](03-borner-archives-ooxml-decompressees.md) | 05 |
| 04 | `blocked` | [Anonymiser le journal de traitement des images](04-anonymiser-journal-images.md) | 05 |
| 05 | `ready-for-agent` | [Rétablir le gate Ruff global](05-retablir-gate-ruff-global.md) | aucun |
| 06 | `ready-for-human` | [Décider le contrat des champs InDesign 2026](06-decider-contrat-champs-indesign-2026.md) | aucun |
| 06A | `conditional` | [Adapter les exports au contrat InDesign 2026](06a-adapter-exports-indesign-2026.md) | 01 à 06 ; activé par comparaison post-tickets à l'oracle 06 |
| 07 | `blocked` | [Recetter les deux parcours sur le jeu officiel et dans InDesign](07-recette-finale-web-script-indesign.md) | 01 à 06 ; 06A s'il est activé |

## Règles globales

- Un ticket par session d'implémentation.
- `ready-for-agent` signifie que toutes les dépendances sont `done`.
- `blocked` signifie que le contrat est fermé mais qu'une dépendance est
  ouverte ; `conditional` n'est jamais une autorisation implicite.
- Ne pas modifier `scripts-2025/`.
- Préserver les modifications locales préexistantes et les données ignorées par
  Git.
- Utiliser des fixtures synthétiques temporaires pour les tickets 01 à 05.
- Ne pas traiter le jeu officiel avant le ticket 07 et une autorisation
  explicite.
- Ne pas inventer les noms de champs InDesign avant clôture du ticket 06.
- Les tickets 01 à 05 conservent la divergence `@pathimg` documentée entre web
  et script ; seul 06 peut activer son adaptation via 06A.
- Ne pas imposer au script le package ou le manifeste propres au web.
- Toute preuve publiée doit utiliser des agrégats et ne contenir aucune donnée
  personnelle ou valeur métier sensible.

## Preuves communes attendues

- tests ciblés du ticket ;
- `uv run --frozen --extra test ruff format --check .` ;
- `uv run --frozen --extra test ruff check .` ;
- `uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q`
  pour toute modification Python partagée avec le web ;
- `git diff --check` et vérification de l'absence de données ou d'artefacts
  suivis.
