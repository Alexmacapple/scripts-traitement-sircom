# 32 - Découper `api/lots.py` sans changer les routes publiques

Statut : `ready-for-agent`

Dépend de : 29C.

À construire : réduire la taille de `sircom2026/api/lots.py` après verrouillage
du contrat public, sans changer les routes, statuts HTTP, codes d'erreur ou
formes JSON.

## Énoncé du problème

`api/lots.py` agrège beaucoup d'endpoints et de helpers de réponse. Un refactor
peut facilement déplacer une précondition, oublier une traduction d'erreur ou
modifier un champ JSON attendu par l'interface.

## Solution

Extraire une responsabilité périphérique et testée, par exemple les builders de
réponses ou les traducteurs d'erreurs, en gardant les routes publiques dans un
état lisible et compatible.

## Critères d'acceptation

- [ ] Le contrat du ticket 29C est présent et vert avant déplacement.
- [ ] Les chemins publics `/api/lots...` ne changent pas.
- [ ] Les statuts HTTP, codes d'erreur et champs JSON contractuels ne changent
      pas.
- [ ] Les helpers extraits restent internes au package API.
- [ ] Les tests API lots, accès, uploads, package et erreurs workflow restent
      verts.
- [ ] Le rapport final liste ce qui a été déplacé et ce qui est resté dans
      `api/lots.py`.

## Hors périmètre

- Changer la politique d'accès.
- Créer une nouvelle version d'API.
- Modifier les workflows métier.
- Refactoriser les modules de domaine appelés par l'API.

## Garde-fous LLM

- Ne pas déplacer toutes les routes en une seule passe.
- Ne pas modifier les signatures de route.
- Ne pas élargir ou réduire les informations exposées par les réponses.

## Preuve attendue

- tests du ticket 29C ;
- `uv run --frozen --extra test pytest -q` ;
- `git diff --check`.
