# 01 - Fusionner les onglets dans la voie scriptée

Statut : `blocked`

Dépend de : 02. Commencer seulement quand 02 est `done`.

À construire : la voie scriptée utilise les deux onglets utiles du classeur
2026 et produit une ligne finale par `Dossier ID`, sans perdre les colonnes ni
les dossiers présents dans une seule source.

## Contexte

Le contrat 2026 désigne `BDD TT + ANALYSE DGDDI` et `Etablissements` comme
onglets utiles à rapprocher par `Dossier ID`. Le runner scripté extrait
actuellement un seul onglet et son étape dite de fusion ne fait qu'un tri de la
feuille active.

Une contre-épreuve synthétique à deux onglets conserve uniquement les colonnes
du premier onglet. La réussite de l'ancien livrable du 24 juillet ne prouve donc
pas le contrat multi-onglets.

## Critères d'acceptation

- [ ] Le runner lit explicitement les deux onglets utiles configurés.
- [ ] Les lignes masquées restent exclues des deux onglets.
- [ ] La fusion utilise `Dossier ID` comme clé logique et produit l'union des
      identifiants non vides.
- [ ] Un identifiant présent dans un seul onglet reste dans la sortie.
- [ ] Une seule colonne d'identifiant est exportée.
- [ ] Un doublon de clé dans un même onglet est bloquant ; une même clé présente
      dans les deux onglets produit une ligne fusionnée.
- [ ] L'ordre de sortie est `id_dossier`, `imageid`, `@pathimg`, puis les
      colonnes sources dans l'ordre des onglets et des colonnes du classeur.
- [ ] Les mappings CSV UTF-8 avec BOM et XLSX contiennent, dans cet ordre :
      `Onglet source`, `Index colonne source`, `Lettre colonne source`,
      `Colonne Excel Original`, `Colonne CSV Final`, `Position sortie`,
      `Statut`, `Champ attendu`, `Description`.
- [ ] `Statut` vaut `exporte`, `supprime`, `cle_fusion` ou `systeme`. Pour une
      colonne `supprime`, nom CSV et position sont vides et `Description`
      contient la raison. `Champ attendu` et `Description` préservent la
      configuration InDesign actuelle.
- [ ] Les deux colonnes ID sources ont deux lignes `cle_fusion`, toutes deux
      liées à `id_dossier` en position 1. La colonne CSV unique prend la clé
      canonique définie par 02, y compris pour un dossier présent seulement
      dans le second onglet.
- [ ] `imageid` et `@pathimg` ont deux lignes `systeme`, l'onglet
      `__system__`, les libellés `(Ajouté) imageid` et `(Ajouté) @pathimg`, des
      coordonnées source vides et les positions 2 et 3.
- [ ] Des colonnes homonymes de provenances différentes restent distinctes. Si
      leurs noms CSV nettoyés entrent en collision, le traitement bloque avec
      les deux provenances ; aucun suffixe, priorité ou coalescence n'est
      inventé.
- [ ] La fusion intervient avant la normalisation finale des cellules afin que
      les trous créés sortent en `#N/A`.
- [ ] Le tri région puis département continue d'utiliser les colonnes métier et
      jamais une colonne de code postal.
- [ ] Une fixture synthétique de succès couvre : identifiant commun,
      identifiant exclusif à chaque onglet et ligne masquée.
- [ ] Une fixture synthétique négative provoque une collision de nom CSV et
      prouve le blocage sans écrasement.
- [ ] Le test vérifie les lignes, colonnes, provenance, `imageid`, `@pathimg` et
      cellules `#N/A` du résultat.
- [ ] Le script conserve son contrat `@pathimg` : toute ligne le reçoit depuis
      `imageid`, même si l'image source manque. Ce ticket n'aligne pas le web.
- [ ] La documentation de la voie scriptée ne présente plus un seul onglet
      extrait comme équivalent à une fusion 2026.

## Hors périmètre

- Modifier `scripts-2025/`.
- Imposer au script le package zip ou le manifeste du web.
- Modifier le contrat de fusion du parcours web.
- Modifier le contrat `@pathimg` de l'un ou l'autre parcours.
- Traiter le jeu officiel pendant l'implémentation.

## Preuve attendue

- test automatisé du runner ou de la chaîne scriptée sur un classeur temporaire
  à deux onglets ;
- contrôle agrégé du CSV synthétique UTF-16 ;
- commandes Ruff du dépôt ;
- `git diff --check`.

## Sources locales

- `AGENTS.md`
- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `re-run-old-script-2026/run_jeu_test_2026.py`
- `re-run-old-script-2026/00-extract_departement_to_sircom.py`
- `re-run-old-script-2026/04-fusion_tri_region_departement.py`
- `re-run-old-script-2026/12-create_mapping_excel.py`
