# Contrat données, CSV et images Sircom 2026

Date : 2026-07-21

## Sources

- `AGENTS.md`
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`
- tickets 09 à 22

## Problème

Le flux CSV et le flux images peuvent avancer séparément, mais le package final
doit rester cohérent. La V1 doit aussi éviter d'inventer des règles de mapping,
de tri, de `imageid` ou de compatibilité InDesign au moment du code.

## Upload et diagnostic Excel

- Format accepté V1 : `.xlsx` OOXML exploitable par `openpyxl`.
- Les limites de taille sont celles de la configuration V1.
- L'upload crée un artefact `excel_source`.
- Aucun chemin disque interne n'est renvoyé.
- Le diagnostic peut produire des problèmes bloquants, alertes ou informations.
- Les valeurs de cellules ne sont pas journalisées.
- Les erreurs Excel sale affichent titre, cause, emplacement, action et détails
  techniques dépliables.

Refus V1 :

- cellules fusionnées ;
- en-têtes multi-lignes ;
- colonnes masquées ;
- lignes masquées ;
- onglets masqués ;
- formules ;
- colonne avec données sans en-tête ;
- impossibilité d'identifier `id_dossier` ;
- doublons `id_dossier` dans un même onglet utile ;
- collisions de noms CSV après nettoyage non résolues.

## Mapping

Le mapping persiste une décision de structure, jamais des valeurs métier.

Champs de mapping par colonne :

- onglet source ;
- index et lettre Excel ;
- nom original ;
- rôle logique optionnel ;
- statut `exporte` ou `supprime` ;
- nom CSV final ;
- raison de suppression optionnelle ;
- fingerprint de structure.

Rôles logiques V1 :

- `id_dossier` ;
- `date` ;
- `region` ;
- `departement` ;
- `nom_image_source` ;
- `siret` ;
- `telephone` ;
- `code_postal` ;
- `code_administratif` ;
- `texte`.

Les profils de mapping sont globaux, réutilisables comme brouillon seulement.
Une compatibilité de profil est calculée par fingerprint de structure :

- noms d'onglets ;
- ordre des onglets ;
- en-têtes ;
- colonnes détectées comme `id_dossier` ;
- version de règle de nettoyage.

Même compatible, un profil n'est jamais appliqué silencieusement : l'utilisateur
doit valider.

## Nommage CSV

Règle par défaut issue de 2025 :

- préfixe lettre Excel ;
- minuscules ;
- sans accents ;
- sans caractères spéciaux ;
- 10 caractères maximum.

Exceptions V1 non nettoyées :

- `id_dossier` ;
- `imageid` ;
- `@pathimg`.

En multi-onglets, la provenance onglet + lettre + nom original reste visible
dans l'UI et le rapport. Si deux noms CSV finaux entrent en collision après
nettoyage, le mapping est bloqué jusqu'à renommage humain.

## Fusion multi-onglets

- Fusion à plat par clé logique `id_dossier`.
- Une seule colonne `id_dossier` exportée.
- Ordre source stable : ordre des onglets du classeur, puis ordre des lignes
  dans l'onglet.
- Pour un `id_dossier` présent dans plusieurs onglets, la ligne fusionnée garde
  le premier rang source rencontré comme `source_rank`.
- Ligne sans `id_dossier` : supprimée, comptée et signalée.
- `id_dossier` dupliqué dans un onglet utile : bloquant.

## Normalisation

- Retours ligne convertis en `<br>`.
- Espaces début/fin supprimés.
- Espaces multiples réduits.
- Dates confirmées ou détectées converties en `dd/mm/yyyy`.
- Dates invalides : `#N/A` dans le CSV, problème structuré.
- Champs sensibles conservés en texte : `id_dossier`, SIRET, téléphone, code
  postal, département et codes administratifs.
- Colonnes entièrement vides supprimées après normalisation, même sélectionnées.
- Exceptions à la suppression : `id_dossier`, `imageid`, `@pathimg`.

## Tri

Le tri région/département est une étape métier distincte.

- Si les rôles `region` et `departement` sont présents, l'application propose le
  tri.
- L'utilisateur confirme le tri ou conserve l'ordre source.
- Comparateur V1 : casse ignorée, accents retirés, valeurs vides en fin.
- À égalité, l'ordre `source_rank` est conservé.
- Si les colonnes ne sont pas détectées, alerte non bloquante et ordre source
  conservé.

## Contrat CSV

La V1 garantit le format du CSV 2025 :

- UTF-16 little endian avec BOM `FF FE` ;
- séparateur virgule ;
- fins de ligne LF ;
- guillemets automatiques seulement si nécessaire ;
- cellules métier vides remplacées par `#N/A` ;
- absence de cellules vides dans les lignes exportées ;
- absence de `N/C` et équivalents hérités ;
- `imageid` et `@pathimg` juste après `id_dossier`.

Deux gates sont distincts :

- `csv_exportable` : Excel accepté, mapping validé, fusion/normalisation/tri,
  vérificateur CSV OK, aucun problème bloquant ouvert.
- `package_exportable` : `csv_exportable`, rapports courants, snapshot images
  courant ou décision explicite de continuer sans images.

## Gabarit InDesign

La V1 ne promet pas automatiquement la compatibilité des noms de champs avec le
gabarit InDesign 2026.

Tant que le Sircom n'a pas confirmé le gabarit :

- l'application garantit le format CSV ;
- elle affiche ou documente que l'import réel dans InDesign reste à tester ;
- elle n'ajoute pas d'adaptateur legacy `b_id` / `a_madeinfr` sans décision
  explicite.

## Images et ImageBindings

Le flux images est optionnel pour le CSV, mais nécessaire au package avec images.

États du flux images :

- `non_fourni` ;
- `ignore_par_utilisateur` ;
- `inspecte` ;
- `traite` ;
- `termine_avec_alertes` ;
- `bloque`.

L'utilisateur peut confirmer "continuer sans images". Cette décision crée un
snapshot `ImageBindings` courant sans images retenues.

Un `ImageBinding` par `id_dossier` contient :

- `id_dossier` ;
- statut `matched`, `missing`, `ignored`, `ambiguous`, `conversion_failed` ;
- nom source si autorisé avant purge ;
- artifact source ;
- nom final ;
- SHA-256 final si image produite ;
- décision utilisateur éventuelle ;
- fingerprint du zip et des règles.

Sémantique V1 :

- `imageid` est déterministe pour chaque ligne avec `id_dossier` valide :
  `{id-normalise}.jpg` ;
- `@pathimg` est rempli seulement si une image finale existe ;
- lorsqu'il est rempli, `@pathimg` vaut
  `{SIRCOM_INDESIGN_IMAGE_ROOT}/{id-normalise}.jpg`, avec
  `/Users/victoria/Documents/export-jpg-resize` par défaut ;
- `@pathimg` reste vide si image absente, ignorée, ambiguë non résolue ou si
  l'utilisateur continue sans images.

## Upload zip images

- Un seul zip images courant par lot.
- Toute image en sous-dossier est refusée en V1.
- Exceptions techniques ignorables : `__MACOSX/` et `.DS_Store`.
- Zip slip, chemins absolus et liens dangereux sont bloquants.
- Inspection et traitement images passent par worker avec progression.
- Les limites de taille, nombre d'images et décompression sont celles de la
  configuration.

## Matching et traitement images

Niveaux de matching :

1. exact sur nom de fichier sans extension ;
2. toléré après normalisation casse, espaces, tirets, underscores et extension ;
3. suggestion non automatique pour ressemblances partielles ;
4. ambiguïté à résoudre manuellement.

Images non référencées : ignorées mais listées dans le rapport.

Images finales :

- format JPG ;
- nom `{id-normalise}.jpg` ;
- largeur maximale 350 px ;
- qualité JPEG 100 ;
- DPI 300 ;
- orientation EXIF appliquée ;
- fond blanc pour transparence ;
- dossier final du package : `export-jpg-resize/`.

## Rapports et package

Rapports métier :

- mapping utilisé avec provenance complète ;
- compteurs source et sortie ;
- lignes sans `id_dossier` supprimées ;
- colonnes vides supprimées ;
- dates invalides ;
- alertes Excel ;
- alertes images ;
- décisions utilisateur.

`mapping-utilise.json` contient le mapping validé, les rôles, les noms CSV, les
fingerprints et la provenance, sans valeurs métier.

Le manifeste du package :

- liste les entrées du package ;
- contient tailles et SHA-256 ;
- n'inclut pas son propre hash ;
- référence la version des règles.

Si l'utilisateur continue sans images, le package reste possible : le dossier
`export-jpg-resize/` est présent dans la structure du package, mais ne contient
aucune image métier.

## Tests obligatoires

- Test golden CSV au niveau octets contre le CSV 2025 de référence.
- Test collision de noms CSV après nettoyage.
- Test profil de mapping appliqué comme brouillon seulement.
- Test tri avec accents, casse, valeurs vides et égalités.
- Test CSV sans images après confirmation utilisateur.
- Test changement zip ou résolution image invalidant aperçu CSV, rapports et
  package.
- Test `ImageBindings` : image présente, absente, ignorée, ambiguë, conversion
  échouée.
- Test zip avec image en sous-dossier refusé et `__MACOSX/` ignoré.
