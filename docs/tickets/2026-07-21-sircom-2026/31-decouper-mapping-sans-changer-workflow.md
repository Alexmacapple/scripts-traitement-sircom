# 31 - Découper `mapping.py` sans changer le workflow mapping

Statut : `ready-for-agent`

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

- [ ] Le contrat du ticket 29B est présent et vert avant déplacement.
- [ ] Une responsabilité cohérente est extraite dans un module dédié.
- [ ] Les imports publics utilisés par l'API et les tests restent compatibles.
- [ ] Le mapping par défaut, la validation, les profils et l'invalidation aval
      gardent le même comportement.
- [ ] Les tests mapping, CSV preview et invalidation restent verts.
- [ ] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
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
