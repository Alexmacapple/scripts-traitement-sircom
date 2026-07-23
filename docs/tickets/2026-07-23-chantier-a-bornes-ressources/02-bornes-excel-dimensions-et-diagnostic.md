# 02 - Bornes Excel dimensions et diagnostic

Statut : `done`

Dépend de : 01.

À construire : un Excel hors limites dimensionnelles est refusé rapidement avec
une erreur structurée, sans lancer de diagnostic non borné.

## Contexte

L'upload Excel vérifie actuellement l'extension, la taille en octets, le contenu
vide et la lisibilité du classeur. Le diagnostic parcourt ensuite les feuilles et
les cellules utiles. Les revues signalent qu'un classeur peu volumineux mais aux
dimensions extrêmes peut déclencher un parcours trop coûteux.

## Critères d'acceptation

- [x] Un classeur qui dépasse les limites de lignes, colonnes ou cellules
      parcourues est refusé avec le code stable
      `SIRCOM_EXCEL_DIMENSIONS_EXCEEDED`.
- [x] Si le dépassement est détectable pendant la validation d'upload sans scan
      complet, l'API retourne `422` ; si le dépassement n'est découvert que dans
      le diagnostic, l'étape est bloquée avec un problème structuré visible dans
      le lot.
- [x] Le refus contient des détails non sensibles : limite dépassée, feuille si
      disponible, valeur observée ou compteur atteint.
- [x] Le contrôle ne dépend pas uniquement de `max_row` ou `max_column` :
      l'itération réelle est bornée et s'arrête dès qu'une limite est atteinte.
- [x] Un classeur proche des limites et structurellement sain reste accepté.
- [x] L'API retourne une erreur structurée, pas une exception brute.
- [x] Les problèmes persistés ou affichables restent en français côté UI.
- [x] Les tests couvrent au minimum : trop de lignes, trop de colonnes, trop de
      cellules parcourues, classeur valide proche de la limite, archive
      corrompue toujours refusée comme avant.
- [x] Les tests adversariaux abaissent les limites de configuration pour rester
      rapides ; ils ne génèrent pas de vrais classeurs géants.

## Hors périmètre

- Changement des règles métier de détection `id_dossier`.
- Refactor large du diagnostic Excel.
- Support de formats autres que `.xlsx` et `.xlsm`.

## Preuve attendue

- Tests ciblés upload ou diagnostic Excel.
- La suite existante d'upload Excel reste verte.
- `uv run --frozen --extra test ruff check .`

## Sources locales

- `sircom2026/excel_upload.py`
- `sircom2026/excel_diagnostic.py`
- `sircom2026/excel_diagnostic_pipeline.py`
- `tests/`
- `docs/audits/2026-07-23-contre-revue-glm.md`
