# Fiabilisation des parcours Sircom 2026 avant usage réel

Date : 2026-07-28

## Publication

Mode choisi par l'utilisateur : dossier Markdown local avec un fichier par
ticket.

Tickets associés :
`docs/tickets/2026-07-28-fiabilisation-parcours-sircom-2026/`.

Cette spec est le contrat courant pour son périmètre. Elle amende explicitement
les contrats du 21 et du 23 juillet sur les sujets listés ci-dessous ; elle ne
rouvre aucun ticket historique livré.

La seule frontier agent immédiate est le ticket 05. Les tickets 02, 03 et 04
s'ouvrent après 05 ; le ticket 01 s'ouvre après 02. Le ticket 06 est une
décision humaine lançable en parallèle. Après clôture de 01 à 06, une
comparaison structurelle avec la décision 06 active ou non le ticket 06A. Le
ticket 07 reste bloqué jusqu'à clôture de toutes ses dépendances.

## Sources

- `AGENTS.md`
- `README.md`
- `TODO.md`
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-execution-stockage-worker-sircom-2026.md`
- `docs/specs/2026-07-21-contrat-exploitation-purge-sircom-2026.md`
- `docs/specs/2026-07-21-contrats-implementation-sircom-2026.md`
- `docs/specs/2026-07-23-chantier-a-bornes-ressources-sircom-2026.md`
- `re-run-old-script-2026/README.md`
- `re-run-old-script-2026/docs/`
- audit contradictoire exécuté le 2026-07-28 sur le SHA
  `28ccb29db3e8ae1cf5d8717b9188968003947c83`

## Énoncé du problème

Le parcours web Sircom 2026 franchit ses tests synthétiques, son workflow de
bout en bout et ses contrôles navigateur, mais son upload Excel ne borne pas le
contenu OOXML décompressé avant le chargement par openpyxl. La compatibilité
réelle du CSV avec les noms de champs du gabarit InDesign 2026 reste par ailleurs
non décidée. Le diagnostic web traite aussi encore comme une simple alerte une
ligne métier masquée, alors que le contrat web la rend bloquante.

La voie scriptée produit un ancien livrable dont les agrégats respectent les
principaux contrats CSV et images. Son chemin d'exécution actuel n'est toutefois
pas fidèle au contrat multi-onglets : il extrait un seul onglet et l'étape
nommée « fusion » ne fait qu'un tri. Une modification locale préexistante peut
en outre supprimer silencieusement des identifiants non numériques lorsque
l'en-tête vaut `ID`, puis annoncer une intégrité positive.

Enfin, le gate Ruff format échoue sur l'état audité et le journal image scripté
duplique des identifiants et noms métier dans un artefact persistant.

## Solution

Rendre les deux parcours utilisables selon leurs contrats propres, sans les
forcer à produire des packages identiques :

- faire réellement fusionner les deux onglets utiles par `Dossier ID` dans la
  voie scriptée ;
- traiter les identifiants comme des textes opaques et ne supprimer que les
  identifiants vides ;
- inspecter et borner la structure OOXML avant openpyxl, puis rétablir le refus
  web des lignes métier masquées ;
- séparer les traces techniques anonymisées des informations métier nécessaires
  au traitement des images ;
- restaurer les gates Ruff définis par la CI ;
- obtenir une décision Sircom sur les noms de champs InDesign 2026 ;
- terminer par une recette réelle comparée, explicitement autorisée, sans
  publier de données sensibles.

Le parcours web reste le candidat principal. La voie scriptée reste une
alternative isolée destinée à produire le CSV UTF-16, les images traitées, le
mapping et le résumé prévus par sa documentation. Cette spec ne lui impose pas
le manifeste ni le package zip propres au web.

## Récits utilisateurs

1. En tant qu'agent Sircom, je veux que toutes les données des onglets utiles
   soient fusionnées par dossier, afin que le CSV ne perde aucun établissement
   ou champ attendu.
2. En tant qu'agent Sircom, je veux que mes identifiants restent exacts hors
   retrait explicite des espaces périphériques, y compris s'ils contiennent des
   lettres ou des zéros initiaux, afin d'éviter toute suppression silencieuse.
3. En tant qu'utilisateur de l'application web, je veux qu'un Excel hostile soit
   refusé avant de saturer le poste, afin de conserver une application locale
   disponible.
4. En tant qu'exploitant, je veux des journaux techniques sans données métier
   brutes et un rapport métier actionnable, afin de diagnostiquer sans multiplier
   les copies sensibles.
5. En tant que mainteneur, je veux que les commandes Ruff de la CI passent sur
   le dépôt, afin que les régressions fonctionnelles puissent atteindre les
   tests.
6. En tant que responsable Sircom, je veux valider les champs attendus par le
   gabarit InDesign 2026, afin que la recette teste le bon contrat.
7. En tant que décideur, je veux une recette finale distincte des deux parcours,
   afin de prononcer un GO, un GO conditionnel ou un NO-GO sur des preuves
   actuelles.

## Décisions d'implémentation

- Les onglets utiles du jeu 2026 sont `BDD TT + ANALYSE DGDDI` et
  `Etablissements`. Dans la voie scriptée, les lignes masquées sont exclues.
  Dans le web, toute ligne masquée située après l'en-tête détecté et contenant
  au moins une cellule non vide dans un onglet candidat à l'import est un
  diagnostic bloquant `SIRCOM_EXCEL_HIDDEN_ROWS`. Une ligne masquée entièrement
  vide n'est pas une ligne métier et ne bloque pas. La clé commune reste
  `Dossier ID`.
- La fusion scriptée suit le contrat web : union des identifiants non vides,
  une ligne finale par identifiant et provenance déterministe des colonnes.
- Un doublon de clé dans un même onglet est bloquant. Une même clé présente
  dans les deux onglets produit une seule ligne fusionnée.
- Les sorties scriptées de mapping, CSV UTF-8 avec BOM et XLSX, contiennent
  exactement ces colonnes dans cet ordre : `Onglet source`,
  `Index colonne source`, `Lettre colonne source`,
  `Colonne Excel Original`, `Colonne CSV Final`, `Position sortie`, `Statut`,
  `Champ attendu`, `Description`.
- `Statut` vaut `exporte`, `supprime`, `cle_fusion` ou `systeme`. Une colonne
  `supprime` a `Colonne CSV Final` et `Position sortie` vides ; sa raison figure
  dans `Description`. Les colonnes exportées commencent en position 4.
  `Champ attendu` et `Description` conservent la configuration InDesign
  existante. Aucune valeur métier n'est stockée dans le mapping.
- Les deux colonnes sources d'identifiant ont le statut `cle_fusion`, le nom
  final `id_dossier` et la position 1. Elles restent deux lignes de provenance,
  mais ne créent qu'une colonne CSV. Les lignes `imageid` et `@pathimg` ont le
  statut `systeme`, l'onglet `__system__`, les libellés originaux
  `(Ajouté) imageid` et `(Ajouté) @pathimg`, des coordonnées source vides et
  les positions 2 et 3. Aucune ligne synthétique supplémentaire n'est créée
  pour `id_dossier`.
- L'ordre de sortie est `id_dossier`, `imageid`, `@pathimg`, puis les colonnes
  sources dans l'ordre des onglets et des colonnes du classeur.
- Deux colonnes homonymes issues de provenances différentes restent deux
  colonnes distinctes. Si leurs noms CSV nettoyés entrent en collision, le
  traitement est bloqué avec les deux provenances dans le diagnostic. Il n'y a
  ni suffixe automatique, ni priorité implicite, ni coalescence.
- Les trous créés par la fusion sont normalisés en `#N/A` avant l'export final.
  Une collision de colonnes ne doit jamais écraser silencieusement une valeur.
- Un identifiant dossier est une chaîne Unicode opaque. La clé canonique retire
  seulement les espaces périphériques ; elle préserve casse, ponctuation,
  séparateurs et espaces internes. Une valeur vide après ce retrait est
  absente. Deux valeurs devenues identiques après ce retrait sont des doublons.
- Ce contrat de type, de canonicalisation et de collision s'applique au web et
  à la voie scriptée, dès le ticket 02.
- La valeur exportée dans `id_dossier` est cette clé canonique. La valeur brute
  d'un onglet n'est jamais choisie comme variante de sortie.
- Une cellule Excel textuelle conserve notamment ses zéros initiaux. Une cellule
  numérique est acceptée seulement si elle n'est pas booléenne, est finie,
  mathématiquement entière, strictement comprise entre `-10^15` et `10^15`, et
  si son format Excel vaut `General` ou `0`. Elle devient sa représentation
  décimale ASCII sans séparateur ni suffixe `.0`.
- Sont refusés avec le code `SIRCOM_ID_REQUIRES_TEXT` : booléen, date ou heure,
  erreur, formule, nombre non entier ou non fini, nombre hors de la plage
  ci-dessus et tout autre format numérique. Le diagnostic indique l'onglet et
  la cellule, jamais la valeur. Un format visuel ne permet pas de reconstruire
  sûrement un identifiant.
- Les alias acceptés, notamment `Dossier ID`, `id_dossier` et `ID`, appliquent
  exactement cette même règle. La normalisation distincte destinée à
  `imageid` ne transforme pas la clé en contrainte numérique.
- Le stem d'`imageid` applique exactement à la clé canonique : Unicode NFKD,
  translittération ASCII par suppression des caractères non représentables,
  minuscules, suppression de tous les espaces et points, puis suppression de
  tout caractère hors `[a-z0-9_-]`. Un stem vide devient `sans-id` et
  `imageid` vaut `{stem}.jpg`, sans préfixe.
- Deux clés distinctes produisant le même `imageid` sont un blocage explicite
  dans les deux parcours ; aucune image ni ligne n'est écrasée et aucun suffixe
  n'est inventé. Le web applique ce blocage avant tout aperçu ou export CSV,
  même si aucun ZIP images n'est fourni.
- Les contrôles OOXML interviennent avant tout appel coûteux à openpyxl. Ils
  bornent au minimum le nombre de membres, la taille décompressée cumulée, la
  taille d'un membre et les ratios de compression anormaux.
- Les bornes OOXML suivent le modèle existant des limites configurables
  `SIRCOM_*`, sont exposées sans chemin interne dans les limites publiques et
  produisent une erreur API structurée.
- Les valeurs V1 sont :
  `SIRCOM_MAX_OOXML_MEMBERS=4096`,
  `SIRCOM_MAX_OOXML_UNCOMPRESSED_MB=256`,
  `SIRCOM_MAX_OOXML_MEMBER_MB=64` et
  `SIRCOM_MAX_OOXML_COMPRESSION_RATIO=100`. Elles sont configurables et
  s'appliquent aux fichiers `.xlsx` et `.xlsm`. Ici, `MB` conserve la convention
  du projet : `1 MiB = 1 048 576 octets`. Les quatre valeurs sont des entiers
  strictement positifs validés au démarrage ; le ratio doit être au moins 1.
- Le nombre couvre toutes les entrées de la table centrale. La taille cumulée
  est la somme des tailles décompressées. Le ratio est contrôlé par membre et
  globalement avec
  `taille_decompressee / max(taille_compressee, 1)`. Une valeur égale à la
  limite est acceptée ; seul un dépassement strict est refusé. Un membre non
  vide de taille compressée nulle est refusé.
- Pour chaque nom brut de membre, l'ordre est impératif : refuser d'abord
  l'octet nul ; remplacer `\` par `/` et appliquer Unicode NFC ; refuser ensuite
  un nom commençant par `/`, un préfixe de lecteur `^[A-Za-z]:` ou tout segment
  exactement égal à `..` ; seulement après, retirer les segments vides et `.`,
  joindre par `/` et appliquer `casefold()` pour la détection des doublons.
- Sont également refusés avant `openpyxl` : doublon de nom canonique, lien
  symbolique, type spécial et membre chiffré. Une macro embarquée n'est jamais
  exécutée. Les tests négatifs couvrent au moins `/xl/...`, `\xl\...`,
  `C:/xl/...`, `../xl/...` et `xl/../...`.
- Un dépassement renvoie
  HTTP 413, `SIRCOM_EXCEL_ARCHIVE_LIMIT_EXCEEDED` et le seul détail public
  `limit`, parmi
  `members`, `uncompressed_total`, `uncompressed_member`,
  `compression_ratio_member` et `compression_ratio_total`. Une archive
  structurellement dangereuse renvoie HTTP 422,
  `SIRCOM_EXCEL_ARCHIVE_INVALID` et le seul détail public `reason`, parmi
  `invalid_zip`, `nul_byte`, `absolute_path`, `drive_prefix`,
  `parent_segment`, `duplicate_member`, `link_member`, `special_member` et
  `encrypted_member`. Aucun chemin interne ni nom de membre n'est exposé.
- `GET /api/config/limits` publie ces valeurs sous `excel.archive` avec les clés
  `max_members`, `max_uncompressed_mb`, `max_member_mb` et
  `max_compression_ratio`.
- Le journal technique scripté contient des compteurs, codes stables et
  références opaques propres au run, au format `img-000001`. Il ne contient ni
  identifiant dossier, ni nom de fichier source ou final, ni chemin métier, ni
  valeur de cellule. Une référence n'est jamais dérivée par hash d'une valeur
  métier et n'est pas stable entre deux runs.
- Les détails métier nécessaires à la correction des images sont isolés dans
  `rapport-images-sensible.csv`, encodé en UTF-8 avec BOM, sous le dossier de
  sortie déjà ignoré par Git. Ses colonnes sont, dans cet ordre :
  `reference_technique`, `statut`, `id_dossier`, `nom_source`, `nom_final`,
  `candidats`, `action`.
- Le rapport contient une ligne seulement pour chaque dossier au statut
  `missing`, `ambiguous` ou `conversion_failed`, dans l'ordre de traitement. Il
  est créé même sans anomalie, avec son seul en-tête.
- `candidats` est un tableau JSON compact de noms triés selon leur chaîne
  Unicode exacte ; il vaut `[]` hors ambiguïté. `action` vaut respectivement
  `provide_source`, `select_candidate` ou `replace_or_convert_source`.
  `nom_source` est vide sans source sélectionnée. Les cellules vides de ce
  rapport opérateur ne relèvent pas du contrat CSV InDesign.
- Le CSV sensible utilise la virgule, les fins de ligne LF et les guillemets
  CSV standards. Il est créé atomiquement avec des permissions propriétaire
  seul (`0600`) sur système POSIX.
- Il n'est jamais inclus dans `images-processing-*.log`,
  `run-2026-summary.json`, une archive ou un package. Il est ajouté aux sorties
  connues de `--clean` et suit exactement la rétention du dossier de sortie,
  sans copie secondaire. Le résumé JSON ne publie que les compteurs par statut.
- Les exceptions écrites sur la console, stderr ou dans un journal persistant
  sont réduites à une classe et un code stable ; elles ne recopient pas de
  chemin, nom ou valeur brute.
- Le rétablissement Ruff est une modification mécanique sans changement de
  comportement.
- Les noms de champs InDesign 2026 ne sont pas inventés. Leur choix relève du
  ticket humain 06. Le ticket 06 fixe la cible, sans la comparer à un export
  encore susceptible de changer.
- Jusqu'à cette décision, la divergence `@pathimg` est conservée : la voie
  scriptée le renseigne pour toute ligne depuis `imageid`, même si l'image
  manque ; le web le renseigne seulement lorsqu'une image finale existe. Les
  deux utilisent la racine configurable, avec la racine HFS à deux-points
  documentée comme valeur par défaut.
- L'absence de cellule métier vide reste obligatoire. Le `@pathimg` vide du web
  est l'unique exception système prévue par cette spec.
- Le traitement du jeu réel et l'import InDesign ne commencent qu'après une
  autorisation explicite et dans le ticket 07.
- Une fois 01 à 06 `done`, un contrôle sur les schémas et CSV synthétiques
  post-tickets compare chaque parcours à la cible 06. Il consigne
  `06A activé` si un écart existe, sinon `06A non activé` avec la preuve de
  comparaison. Cette décision n'est jamais prise sur l'export préexistant au
  ticket 01.

Ces valeurs OOXML sont volontairement conservatrices au regard de la limite
d'upload actuelle de 50 Mio. Elles bornent le pire cas mémoire avant
`openpyxl` et refusent notamment la contre-épreuve de 4,2 Mio décompressés pour
environ 10 Kio compressés par son ratio supérieur à 100. Une fixture saine sous
les quatre seuils doit rester acceptée. Le ticket 07 peut établir qu'un
relèvement est nécessaire sur le jeu autorisé ; il ne peut pas modifier
silencieusement les valeurs pendant la recette.

## Décisions de test

- Seam script haut niveau : un classeur synthétique contenant les deux onglets
  utiles produit l'union des dossiers, les colonnes des deux sources, le mapping
  de provenance et aucun doublon de clé. Une seconde fixture provoque une
  collision de nom CSV et vérifie le blocage sans écrasement.
- Seam identifiant : les variantes numérique, alphanumérique, avec zéro initial,
  espaces périphériques, ponctuation, format numérique à zéros et valeur vide
  ont le résultat défini ci-dessus.
- Seam `imageid` : ponctuation de chemin, accents, casse, espaces, points,
  caractère non translittérable et deux identifiants convergents vérifient
  l'algorithme exact et le blocage de collision.
- Seam web : un OOXML de petite taille compressée mais dépassant une borne
  décompressée configurée est rejeté avant openpyxl avec un code stable.
- Seam diagnostic web : une ligne métier masquée rend le classeur non
  importable avec `SIRCOM_EXCEL_HIDDEN_ROWS`, tandis qu'une ligne masquée
  entièrement vide ne bloque pas.
- Seam confidentialité : des sentinelles synthétiques d'identifiant et de nom
  d'image sont absentes du journal technique standard et présentes seulement,
  si nécessaire, dans le rapport métier prévu.
- Seam CI : les commandes Ruff exactes du workflow retournent zéro.
- Seam humain : le gabarit InDesign final importe le CSV et résout les champs
  convenus sans remapping improvisé.
- Seam de recette : chaque parcours est exécuté selon sa documentation, puis
  contrôlé sur le CSV, le tri, `imageid`, `@pathimg`, les images, rapports et
  artefacts qu'il promet réellement.

Les tests adversariaux utilisent des seuils abaissés et des fichiers temporaires
synthétiques. Ils ne fabriquent pas de vrais fichiers géants et n'ouvrent pas de
données réelles.

## Hors périmètre

- Modifier `scripts-2025/`.
- Aligner artificiellement le packaging de la voie scriptée sur le package web.
- Ajouter une authentification distante, un VPS, Celery, Redis ou une SPA.
- Refaire l'architecture FastAPI, SQLite, worker ou artefacts déjà couverte.
- Auditer de nouveau l'ensemble RGAA ou toutes les dépendances.
- Corriger le code dans la même session que la rédaction de cette spec.
- Lancer Loriq, committer, pousser ou publier des issues GitHub.

## Questions ouvertes

- Unknown : le gabarit InDesign 2026 attend-il les nouveaux noms
  `id_dossier` et noms mappés, ou les champs historiques 2025 tels que `b_id`
  et `a_madeinfr` ?

La présence réelle de l'alias d'en-tête `ID` reste inconnue, mais ne demande
aucune décision d'implémentation : s'il est accepté, il suit le contrat
d'identité ci-dessus.

## Notes complémentaires

L'audit du 2026-07-28 a observé :

- 296 tests Python réussis, 8 ignorés et une couverture de 89,86 % ;
- 6 tests navigateur et Axe réussis après activation explicite ;
- un ancien CSV scripté de 561 lignes et 20 colonnes, avec 392 cellules `#N/A`,
  aucune cellule vide et aucune inversion de tri observée ;
- une contre-épreuve synthétique où l'onglet `Etablissements` disparaît de la
  voie scriptée ;
- une contre-épreuve synthétique où un identifiant alphanumérique sous `ID` est
  supprimé avec un code de sortie nul ;
- une archive OOXML synthétique de 10 353 octets contenant 4 213 284 octets
  décompressés, acceptée malgré une limite d'upload configurée à 1 Mio ;
- `ruff check .` vert et `ruff format --check .` en échec sur six fichiers.

Ces preuves sont synthétiques ou locales. Elles ne remplacent pas la recette
réelle du ticket 07.
