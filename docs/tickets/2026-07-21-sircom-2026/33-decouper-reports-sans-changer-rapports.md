# 33 - Découper `reports.py` sans changer les rapports générés

Statut : `ready-for-agent`

Dépend de : 29D.

À construire : réduire la taille et la responsabilité de
`sircom2026/reports.py` après verrouillage du contrat public, sans changer les
rapports générés ni les artefacts associés.

## Énoncé du problème

`reports.py` mélange collecte des données, rendu du rapport métier, rendu du
rapport technique et écriture transactionnelle des artefacts. Un refactor trop
large peut modifier le contenu final ou réintroduire des données sensibles.

## Solution

Extraire une responsabilité cohérente, par exemple le rendu métier ou le rendu
technique, en gardant l'orchestration de job et les écritures transactionnelles
stables.

## Critères d'acceptation

- [ ] Le contrat du ticket 29D est présent et vert avant déplacement.
- [ ] Les noms d'artefacts ne changent pas.
- [ ] Les sections du rapport métier ne changent pas.
- [ ] Le schéma principal du rapport technique ne change pas.
- [ ] Les garanties d'absence de données sensibles restent testées.
- [ ] Les tests rapports, package et CSV preview restent verts.
- [ ] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `reports.py`.

## Hors périmètre

- Améliorer le contenu éditorial des rapports.
- Changer le format JSON technique.
- Modifier le package final.
- Refactoriser d'autres modules lourds.

## Garde-fous LLM

- Ne pas mélanger rendu et écriture d'artefacts dans la même extraction.
- Ne pas supprimer de section au motif qu'elle paraît redondante.
- Ne pas exposer de valeurs métier sensibles dans de nouveaux tests ou logs.

## Preuve attendue

- tests du ticket 29D ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
