# Chantier A - Bornes ressources Sircom 2026

Date : 2026-07-23

## Publication

Mode choisi : dossier Markdown local avec un fichier par ticket. Le dépôt ne
contient pas de tracker formalisé local, et les tickets Sircom 2026 existants
utilisent déjà cette convention.

Tickets associés :
`docs/tickets/2026-07-23-chantier-a-bornes-ressources/`.

## Sources

- `AGENTS.md`
- `docs/audits/2026-07-23-revue-code-fable-flavien.md`
- `docs/audits/2026-07-23-contre-revue-glm.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-execution-stockage-worker-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`
- `docs/tickets/2026-07-21-sircom-2026/09-upload-excel-securise-limites-et-stockage-artefact.md`
- `docs/tickets/2026-07-21-sircom-2026/18-upload-zip-images-et-inspection-securisee.md`
- `docs/tickets/2026-07-21-sircom-2026/20-matching-et-traitement-images.md`

## Énoncé du problème

Les deux revues de code convergent : le socle Sircom 2026 est solide, mais il
reste exposé à des entrées valides en taille disque mais extrêmes en dimensions.
Un Excel peu volumineux mais immense en lignes, colonnes ou cellules parcourues,
ou une image fortement compressée mais énorme en pixels, peut ralentir ou
saturer le poste local pendant le diagnostic, l'inspection ou la conversion.

Le contrôle disque existe en readiness, mais il ne bloque pas encore les jobs
lourds au moment où ils vont produire ou empaqueter des artefacts.

## Solution

Borner explicitement les ressources métier avant les traitements coûteux :

- limites Excel en lignes, colonnes et cellules parcourues ;
- limites images en pixels, largeur et hauteur avant conversion pleine image ;
- garde disque juste avant les jobs lourds ;
- erreurs structurées et problèmes métier lisibles ;
- tests adversariaux prouvant le refus rapide des cas extrêmes ;
- ajout de `ruff check .` dans la CI.

## Récits utilisateurs

1. En tant qu'utilisateur Sircom, je veux qu'un fichier Excel anormal soit refusé
   rapidement, afin que l'application locale ne se bloque pas pendant l'import.
2. En tant qu'utilisateur Sircom, je veux qu'une image produit hors limites soit
   signalée clairement, afin de corriger le zip sans perdre le lot.
3. En tant qu'exploitant local, je veux que les jobs lourds refusent de démarrer
   quand l'espace disque est insuffisant, afin d'éviter des artefacts partiels.
4. En tant que pilote technique, je veux des tests adversariaux en CI, afin que
   les bornes restent actives après les refactorings.

## Décisions d'implémentation

- Ajouter des limites configurables `SIRCOM_MAX_EXCEL_ROWS`,
  `SIRCOM_MAX_EXCEL_COLUMNS`, `SIRCOM_MAX_EXCEL_CELLS`,
  `SIRCOM_MAX_IMAGE_PIXELS`, `SIRCOM_MAX_IMAGE_WIDTH_PX` et
  `SIRCOM_MAX_IMAGE_HEIGHT_PX`.
- Valeurs V1 proposées : 200 000 lignes Excel, 256 colonnes Excel,
  5 000 000 cellules Excel parcourues, 80 000 000 pixels image, 20 000 px en
  largeur et 20 000 px en hauteur.
- La limite cellules est volontairement plus restrictive que le produit lignes x
  colonnes : elle borne le travail total réellement parcouru.
- Exposer ces limites dans les limites publiques de l'application pour garder
  l'UI et les API alignées.
- Pour Excel, refuser en HTTP 422 si le dépassement est détectable sans scan
  lourd pendant l'upload ; sinon bloquer le job de diagnostic avec un problème
  structuré. Ne pas se fier uniquement aux dimensions déclarées par openpyxl ;
  le parcours réel doit aussi être borné.
- Pour les images, faire de l'inspection zip le point propriétaire du
  signalement dimensionnel, puis revalider défensivement au matching avant
  conversion. La limite applicative doit rester cohérente avec la protection
  Pillow, sans la désactiver.
- Pour le disque, réutiliser le seuil existant `SIRCOM_DISK_FREE_MIN_MB` avant
  les jobs qui produisent des artefacts volumineux. Le contrôle est best-effort :
  il réduit le risque mais ne prétend pas réserver l'espace disque.
- Les tests adversariaux doivent abaisser les seuils de configuration pour créer
  de petits fichiers synthétiques. Ils ne doivent pas fabriquer de vrais Excel
  ou images géants.
- Le terme `rcheck` n'a pas été trouvé comme outil local ; la garde CI retenue
  est `uv run --frozen --extra test ruff check .`, en plus du format check
  existant.

## Décisions de test

- Point de contrôle : configuration chargée depuis variables `SIRCOM_*`, valeurs invalides
  refusées, limites visibles via les limites publiques.
- Point de contrôle : upload ou diagnostic Excel rejette un classeur hors dimensions avec une
  erreur structurée et sans lancer un parcours non borné.
- Point de contrôle : inspection ou matching images signale une image hors limites avant
  conversion pleine image.
- Point de contrôle : job lourd matching ou package bloque proprement quand le disque libre
  simulé est sous le seuil.
- Point de contrôle : CI exécute format Ruff, lint Ruff, tests avec couverture et test
  navigateur existant.

## Hors périmètre

- Annulation effective pendant la conversion image.
- Découpage de fichiers volumineux.
- Réalignement complet README/TODO/CHANGELOG.
- Réécriture de la chaîne 2025.
- Passage VPS, Celery, Redis, SPA ou audit RGAA complet.

## Questions ouvertes

- Calibrage exact des limites images à confirmer avec un corpus Sircom réel si
  disponible. Les valeurs V1 sont volontairement hautes pour ne pas rejeter les
  grandes photos produits usuelles.
- Le contrôle disque reste best-effort ; une réservation stricte d'espace n'est
  pas retenue pour la V1 locale.

## Notes complémentaires

Le chantier doit rester conservateur : ajouter des garde-fous et des preuves,
pas refactorer largement les modules déjà fonctionnels.
