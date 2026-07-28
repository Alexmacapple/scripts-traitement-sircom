# 03 - Borner les archives OOXML et refuser les lignes métier masquées

Statut : `blocked`

Dépend de : 05. Commencer seulement quand 05 est `done`.

À construire : l'application web refuse avant transformation un classeur OOXML
dont le contenu interne menacerait les ressources du poste, ainsi qu'un
classeur contenant une ligne métier masquée.

## Contexte

L'upload borne aujourd'hui la taille du corps reçu puis appelle directement
openpyxl. Les limites de lignes, colonnes et cellules s'appliquent après
ouverture du classeur et ne bornent pas les tables de chaînes partagées ni les
autres membres internes de l'archive.

Une archive synthétique de 10 353 octets contenant 4 213 284 octets
décompressés a été acceptée avec une limite d'upload fixée à 1 Mio.

Le diagnostic web actuel classe une ligne masquée contenant des données comme
une alerte et laisse le classeur importable. Ce comportement contredit le
contrat web courant ; la voie scriptée conserve séparément sa règle d'exclusion
des lignes masquées.

## Critères d'acceptation

- [ ] La structure ZIP des fichiers `.xlsx` et `.xlsm` est inspectée avant tout
      chargement openpyxl.
- [ ] Le contrôle borne au minimum le nombre de membres, la taille décompressée
      cumulée, la taille décompressée d'un membre et un ratio de compression
      anormal.
- [ ] Les valeurs par défaut sont
      `SIRCOM_MAX_OOXML_MEMBERS=4096`,
      `SIRCOM_MAX_OOXML_UNCOMPRESSED_MB=256`,
      `SIRCOM_MAX_OOXML_MEMBER_MB=64` et
      `SIRCOM_MAX_OOXML_COMPRESSION_RATIO=100`.
- [ ] `MB` vaut `1 048 576` octets. Les quatre réglages sont des entiers
      strictement positifs validés au démarrage ; le ratio est au moins 1.
- [ ] Le nombre couvre toutes les entrées. Les ratios par membre et global sont
      `taille_decompressee / max(taille_compressee, 1)`. L'égalité à la limite
      est acceptée ; un membre non vide de taille compressée nulle est refusé.
- [ ] L'ordre du contrôle est exact : refuser l'octet nul ; remplacer `\` par
      `/` et appliquer NFC ; refuser ensuite slash initial, préfixe de lecteur
      et segment `..` ; seulement après, retirer les segments vides et `.`,
      joindre par `/` et appliquer `casefold()` pour les doublons.
- [ ] Doublon canonique, lien symbolique, type spécial et membre chiffré sont
      aussi refusés avant le parseur métier.
- [ ] Les tests négatifs couvrent `/xl/...`, `\xl\...`, `C:/xl/...`,
      `../xl/...` et `xl/../...`.
- [ ] Les limites sont configurables selon le modèle `SIRCOM_*`, validées au
      démarrage et exposées dans le contrat public des limites sans chemin
      interne.
- [ ] `GET /api/config/limits` les expose sous `excel.archive` avec
      `max_members`, `max_uncompressed_mb`, `max_member_mb` et
      `max_compression_ratio`.
- [ ] Un dépassement retourne
      HTTP 413, `SIRCOM_EXCEL_ARCHIVE_LIMIT_EXCEEDED` et le seul détail
      `limit` normé. Une structure dangereuse retourne HTTP 422,
      `SIRCOM_EXCEL_ARCHIVE_INVALID` et le seul détail `reason` normé. Aucun nom
      de membre ni chemin interne n'est exposé.
- [ ] Les contrôles existants de taille compressée et de dimensions Excel
      restent actifs.
- [ ] Un OOXML synthétique très compressible et hors limite est refusé sans
      appel à openpyxl.
- [ ] Un OOXML sain proche des limites configurées reste accepté.
- [ ] Les tests couvrent `.xlsx` et `.xlsm` ; aucune macro n'est exécutée.
- [ ] Les tests abaissent les seuils et n'allouent aucun fichier réellement
      volumineux.
- [ ] Toute ligne masquée située après l'en-tête détecté et contenant au moins
      une cellule non vide dans un onglet candidat à l'import rend le
      diagnostic web non importable.
- [ ] Le problème persistant a la sévérité `bloquant` et le code stable
      `SIRCOM_EXCEL_HIDDEN_ROWS`. Sa localisation contient uniquement l'onglet
      et les numéros de lignes concernés, jamais les valeurs des cellules.
- [ ] Une ligne masquée entièrement vide ne bloque pas. Le test synthétique
      distingue explicitement ce cas de la ligne métier masquée.
- [ ] Après ce blocage, aucun job de fusion ou de normalisation et aucun
      artefact de transformation aval ne sont créés ; l'artefact source et le
      diagnostic restent disponibles selon leur contrat existant.
- [ ] La fixture `hidden_row`, son registre et les tests qui verrouillent
      aujourd'hui le statut d'alerte sont alignés sur ce refus.
- [ ] La documentation utilisateur distingue taille uploadée et limites
      internes de l'archive, et distingue le refus web de l'exclusion appliquée
      par la voie scriptée.

## Hors périmètre

- Remplacer openpyxl.
- Modifier les autres règles métier de diagnostic ou de mapping.
- Modifier l'exclusion des lignes masquées dans la voie scriptée.
- Charger le jeu officiel pour calibrer le ticket.
- Relever les valeurs par défaut sans preuve séparée ; le ticket 07 peut
  seulement constater le besoin.
- Généraliser ce ticket aux formats non OOXML.

## Preuve attendue

- tests ciblés de configuration, route publique, upload Excel et diagnostic ;
- espion ou seam équivalent prouvant qu'openpyxl n'est pas appelé après un
  refus structurel ;
- test de pipeline prouvant le blocage avant les transformations aval ;
- suite existante des limites Excel ;
- tests avec couverture et commandes Ruff du dépôt ;
- `git diff --check`.

## Sources locales

- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `docs/specs/2026-07-23-chantier-a-bornes-ressources-sircom-2026.md`
- `docs/tickets/2026-07-23-chantier-a-bornes-ressources/02-bornes-excel-dimensions-et-diagnostic.md`
- `sircom2026/config.py`
- `sircom2026/excel_diagnostic.py`
- `sircom2026/excel_diagnostic_pipeline.py`
- `sircom2026/excel_upload.py`
- `sircom2026/synthetic_excels.py`
- `tests/test_excel_diagnostic.py`
- `tests/test_excel_diagnostic_pipeline.py`
- `tests/test_excel_upload.py`
- `tests/test_web_socle.py`
