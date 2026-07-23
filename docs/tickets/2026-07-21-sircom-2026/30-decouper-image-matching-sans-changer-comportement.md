# 30 - Découper `image_matching.py` sans changer le comportement

Statut : `ready-for-agent`

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

- [ ] Le contrat du ticket 29A est présent et vert avant déplacement.
- [ ] Une responsabilité cohérente est extraite dans un module dédié.
- [ ] Les imports publics utilisés hors module restent compatibles.
- [ ] Aucun statut de binding, code d'erreur, nom final ou artefact ne change.
- [ ] Les tests matching, package, rapports et CSV restent verts.
- [ ] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
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
