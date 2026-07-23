# 04 - Garde disque avant jobs lourds

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

À construire : les jobs qui produisent des artefacts volumineux vérifient
l'espace disque disponible juste avant de travailler et échouent proprement si le
seuil configuré n'est pas respecté.

## Contexte

La readiness vérifie déjà `SIRCOM_DISK_FREE_MIN_MB`, mais cette vérification ne
protège pas directement le lancement d'un job lourd. Le matching images peut
produire un zip en mémoire puis un artefact, et le package final rassemble CSV,
rapports, mapping et images traitées.

## Critères d'acceptation

- [x] Un helper réutilisable vérifie l'espace libre sous `SIRCOM_DATA_DIR` avec
      le seuil `SIRCOM_DISK_FREE_MIN_MB`.
- [x] Les jobs matching images et package final appellent ce helper avant la
      production d'artefacts volumineux.
- [x] Si le disque libre est sous le seuil, le job s'arrête avec un problème
      structuré, par exemple `SIRCOM_DISK_FREE_LOW`, sans produire d'artefact
      partiel commité.
- [x] Le statut final est `bloque` avec un problème `bloquant` ouvert, car
      l'action attendue est opérationnelle et réessayable ; ce n'est pas un 500
      brut ni un échec technique irréversible.
- [x] Les détails du problème indiquent au minimum l'espace libre observé et le
      seuil requis, sans exposer de chemin sensible.
- [x] Le contrôle est testable par simulation de `shutil.disk_usage` ou par
      injection d'un seam équivalent.
- [x] La readiness existante garde son comportement actuel.

## Hors périmètre

- Réservation stricte d'espace disque.
- Refactor du store d'artefacts.
- Changement de la politique de purge.

## Preuve attendue

- Tests ciblés sur le helper disque et au moins un job lourd.
- Vérification que les artefacts ne sont pas committés quand le disque est sous
  le seuil.
- `uv run --frozen --extra test ruff check .`

## Sources locales

- `sircom2026/app_lifecycle.py`
- `sircom2026/image_matching.py`
- `sircom2026/package.py`
- `sircom2026/worker.py`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`
