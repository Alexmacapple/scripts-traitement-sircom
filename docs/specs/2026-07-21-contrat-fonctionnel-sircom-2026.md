# Spec : contrat fonctionnel Sircom 2026

Date : 2026-07-21

Source principale : `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`,
décisions Q0 à Q79.

Spec complémentaire : `docs/specs/2026-07-21-orchestration-sircom-2026.md`
porte les statuts, le worker, SQLite, la reprise, la purge et les traitements de
fond.

## Énoncé du problème

Le Sircom doit produire en 2026 un livrable InDesign à partir d'un Excel
multi-onglets et d'un zip d'images, sans dépendre de scripts locaux lancés à la
main ni d'une structure Excel 2025 codée en dur.

L'application doit permettre de comprendre ce qui a été importé, choisir les
champs utiles, vérifier le CSV final, traiter les images et exporter un package
compatible avec les contraintes InDesign déjà validées en 2025.

## Solution

Construire une interface web autonome, serveur-ready, composée d'un backend
FastAPI avec OpenAPI/Swagger et d'un frontend simple, efficace et aligné avec le
DSFR. L'interface guide l'utilisateur par onglets avec états visibles : import
Excel, mapping, fusion, aperçu CSV, images, rapport et export.

Le coeur fonctionnel reprend la parité utile des scripts 2025, mais généralise
les entrées 2026 : Excel multi-onglets, colonne logique `id_dossier`, mapping
utilisateur, zip images libre, rapport métier et package final.

## Récits utilisateurs

1. En tant qu'agent Sircom, je veux uploader un Excel multi-onglets et savoir
   immédiatement s'il est exploitable, afin de corriger le fichier avant de
   perdre du temps dans le traitement.
2. En tant qu'agent Sircom, je veux choisir les colonnes utiles et vérifier leurs
   noms CSV finaux, afin de produire un fichier compatible InDesign sans exporter
   des champs inutiles.
3. En tant qu'agent Sircom, je veux que l'application fusionne les onglets par
   `id_dossier`, afin d'obtenir une ligne CSV finale par dossier.
4. En tant qu'agent Sircom, je veux téléverser un zip d'images et voir les images
   manquantes, ambiguës ou non référencées, afin de résoudre les écarts avant le
   package final.
5. En tant qu'agent Sircom, je veux prévisualiser les en-têtes, premières lignes,
   suppressions et alertes avant export, afin de valider le résultat métier.
6. En tant qu'agent Sircom, je veux télécharger un package final avec CSV,
   images, rapport et mapping, afin de remettre un livrable exploitable dans
   InDesign.
7. En tant qu'exploitant, je veux des logs techniques séparés du rapport métier,
   afin de déboguer sans exposer inutilement les données métier.

## Décisions fonctionnelles

### Interface et environnement

- L'application cible l'édition Sircom 2026 avec une interface web autonome.
- Développement et préproduction : Mac d'Alex, sans authentification tant que
  l'application n'est pas exposée.
- Production cible : VPS interne, avec authentification existante à intégrer
  plus tard.
- Architecture attendue : backend API, frontend web, stockage temporaire propre,
  configuration par environnement et démarrage local simple.
- Stack décidée : FastAPI avec Swagger/OpenAPI, frontend simple et efficace.
- Frontend : utiliser les composants, espacements, grille et logique DSFR/RGAA
  comme référence de conception.
- Ne pas revendiquer une conformité DSFR ou RGAA sans audit dédié.
- Navigation : onglets libres avec état bloquant. L'export reste bloqué tant que
  les étapes minimales ne sont pas prêtes.

### Import Excel

- Entrée 2026 : un fichier Excel multi-onglets uploadé par l'utilisateur.
- Le CSV 2025 de référence est un output de référence, pas un input.
- Chaque onglet utile doit permettre d'identifier une colonne logique
  `id_dossier`.
- Onglet utile V1 : onglet non vide contenant des données métier à exporter ou à
  utiliser pour la fusion. Un onglet vide est ignoré avec information ; un onglet
  non vide sans `id_dossier` détectable bloque l'import.
- Ne pas coder en dur `B_ID`, `F_ID` ni aucune lettre de colonne 2025.
- Refuser l'import si la structure est ambiguë ou non fiable : cellules
  fusionnées, en-têtes sur plusieurs lignes, colonnes masquées, formules ou
  structure empêchant d'identifier proprement les en-têtes et `id_dossier`.
- Le refus Excel bloque la transformation, mais doit produire un diagnostic clair
  indiquant quoi corriger.
- Les lignes sans `id_dossier` sont supprimées du CSV final et signalées dans le
  rapport.
- Un doublon d'`id_dossier` dans un même onglet n'est pas un scénario métier
  attendu ; il doit être traité comme problème bloquant d'intégrité.

### Mapping

- Le mapping est semi-automatique avec profil réutilisable.
- L'application propose un mapping à partir des noms de colonnes ; l'utilisateur
  confirme et peut sauvegarder le profil.
- L'utilisateur peut sélectionner seulement les champs utiles.
- Sans profil de mapping réutilisé, l'application génère un mapping par défaut :
  toutes les colonnes de tous les onglets utiles sont sélectionnées, puis ce
  mapping doit être validé par l'utilisateur.
- Avec mapping défini, seules les colonnes sélectionnées sont exportées.
- Le mapping interne conserve la provenance complète : onglet source, lettre
  colonne, nom original, nom CSV final, statut exporté ou supprimé.
- Le mapping s'inspire du modèle 2025, étendu au multi-onglets avec provenance
  d'onglet.

### Fusion multi-onglets

- La fusion à plat se fait par clé primaire logique `id_dossier`.
- Une ligne du CSV final correspond à un `id_dossier`.
- L'ensemble des lignes CSV V1 est l'union des `id_dossier` non vides présents
  dans tous les onglets utiles.
- Les colonnes `id_dossier` des autres onglets servent à la fusion interne et ne
  sont pas répétées dans le CSV final.
- Il n'y a pas de feuille principale imposée en V1 ; le modèle s'appuie sur les
  onglets utiles et leur clé commune.
- Si un `id_dossier` existe dans un onglet mais pas dans un autre, la ligne est
  conservée et les champs absents sortent vides dans le CSV final.
- L'ordre des colonnes suit l'ordre du classeur : onglets dans leur ordre, puis
  colonnes dans leur ordre, sauf colonnes ajoutées.
- `imageid` et `@pathimg` sont placés juste après `id_dossier`.

### CSV InDesign

- Le CSV final doit rester compatible avec le fichier InDesign 2025 de
  référence.
- Format exact : UTF-16 avec BOM, séparateur virgule, saut de ligne LF,
  guillemets automatiques seulement si nécessaire.
- Les valeurs vides ou absentes sortent en cellule vide, pas en `#N/A` ni en
  `N/C`.
- Cette règle remplace les décisions intermédiaires Q24, Q48, Q50 et Q51 qui
  envisageaient `#N/A`.
- Les absences restent visibles dans l'interface et dans le rapport.
- Renommage des colonnes : ajouter d'abord la référence de colonne Excel au nom
  original, puis appliquer la règle 2025 : minuscules, sans accents, sans
  caractères spéciaux, longueur maximale 10 caractères.
- La colonne logique exportée pour l'identifiant dossier est nommée
  `id_dossier`. Elle est l'exception métier qui remplace les anciens noms
  dépendants d'une position source comme `b_id` ou `f_id`.
- Exceptions de colonnes ajoutées : `imageid` et `@pathimg`.
- Les colonnes entièrement vides après traitement sont supprimées, même si elles
  avaient été sélectionnées dans le mapping.
- Les retours ligne dans les cellules sont convertis en `<br>`.
- Les espaces en début et fin sont supprimés ; les espaces multiples sont réduits
  à un seul espace.
- Les champs sensibles doivent être préservés comme texte : `id_dossier`, SIRET,
  téléphone, code postal, département et codes administratifs.
- Ne pas modifier automatiquement les prix, pourcentages ou montants sans règle
  explicite.
- Si des colonnes dates sont détectées ou confirmées dans le mapping, convertir
  les valeurs valides au format `dd/mm/yyyy`.
- Les dates invalides ou absentes sont signalées et sortent vides dans le CSV
  final.
- Le tri région puis département est proposé quand les colonnes correspondantes
  sont détectées et doit être confirmé par l'utilisateur.
- Si les colonnes de tri ne sont pas détectées clairement, l'ordre Excel est
  conservé avec alerte non bloquante.

### Aperçu et validation

- L'interface doit proposer un aperçu avant export.
- L'aperçu montre au minimum les en-têtes finaux InDesign, les premières lignes,
  les colonnes supprimées, les lignes supprimées et les alertes.
- L'export est bloqué si l'Excel n'est pas importé, si le mapping n'est pas
  validé, si la colonne `id_dossier` est absente, si aucune colonne n'est
  sélectionnée ou si l'export n'est pas testable.
- Les images manquantes ne bloquent pas l'export CSV ; elles produisent des
  alertes.

### Images

- La V1 gère une image principale par dossier.
- La source images du lot est le zip uploadé par l'utilisateur.
- Le nom du zip est libre ; l'application valide le contenu, pas le nom.
- Un seul zip images est accepté par lot.
- Les images doivent être à la racine du zip.
- Toute image placée dans un sous-dossier du zip est refusée en V1 avec un
  message clair ; seuls les fichiers système explicitement ignorables
  (`__MACOSX/`, `.DS_Store`) peuvent être écartés sans bloquer.
- L'absence de zip images n'empêche pas l'export CSV ; l'application produit une
  alerte forte et indique que le package sera sans images.
- Un zip fourni sans image traitable n'empêche pas l'export CSV ; le rapport
  indique `aucune image traitable`.
- Les images manquantes sont non bloquantes et listées dans l'interface et le
  rapport.
- Les images non référencées sont ignorées pour l'export, mais listées dans
  l'interface et le rapport.
- L'application tente d'abord la correspondance par nom original de fichier si
  une colonne source le permet.
- Si le nom original manque, l'application tente un fallback par `id_dossier`
  normalisé.
- Si une correspondance est trouvée par fallback ou tolérance, elle est signalée
  dans l'interface et le rapport.
- Tolérance automatique : casse différente, espaces en trop, extension
  différente, nom sans extension, tirets et underscores proches.
- Tolérance forte par ressemblance partielle : suggestion uniquement, validation
  manuelle obligatoire.
- Si plusieurs images peuvent correspondre au même dossier, l'application ne
  choisit pas automatiquement ; l'utilisateur sélectionne l'image correcte.
- Le nom final d'image reprend exactement la règle 2025 :
  `dossier-{id-normalise}.jpg`.
- Normalisation de l'ID image : minuscules, suppression des points, suppression
  des espaces, conservation des tirets.
- Les images finales sont converties en JPG avec largeur maximale 350 px,
  qualité JPEG 100 et DPI 300.
- Les images transparentes reçoivent un fond blanc avant conversion JPG.
- L'orientation EXIF est appliquée automatiquement avant conversion.
- Le dossier d'images dans le package final s'appelle `export-jpg-resize/`.
- La colonne `@pathimg` doit viser le chemin InDesign final attendu :
  `/Users/victoria/Documents/export-jpg-resize/...`.
- Formats à accepter selon la logique large 2025 ; minimum à tester : JPG, PNG,
  WEBP, TIFF et HEIC si disponible dans l'environnement.
- Les erreurs images ont deux niveaux : message métier actionnable dans
  l'interface, détails techniques dans les logs.

### Rapport, logs et package

- L'export prioritaire est un package zip complet.
- Si possible, les fichiers principaux restent aussi téléchargeables séparément.
- Le package final contient au minimum le CSV UTF-16, les images renommées et
  optimisées, le rapport et le mapping utilisé.
- Les téléchargements séparés des fichiers principaux sont un confort
  d'interface ; le package zip complet reste le livrable requis de la V1.
- Le rapport inclut le mapping complet : onglet source, lettre colonne, nom
  original, nom CSV final, statut exporté ou supprimé.
- Le rapport inclut une vérification d'intégrité : nombre d'IDs source, nombre
  de lignes CSV, lignes supprimées faute d'`id_dossier`, IDs présents dans
  certains onglets mais absents d'autres, colonnes supprimées et alertes images.
- Les logs 2025 sont une référence informative : informations générales,
  statistiques d'exécution, étapes exécutées, fichiers créés, résultat final,
  paramètres images, correspondances CSV/images, erreurs et résumé.
- En 2026, distinguer rapport métier et logs techniques.
- Les logs techniques ne doivent pas exposer inutilement les données
  personnelles ou contenus métier dans l'interface.

### Volumes et traitements longs

- Les gros traitements, notamment zip images et conversion images, ne doivent pas
  dépendre d'une requête HTTP longue.
- L'interface doit afficher une progression, les étapes réalisées, les erreurs
  métier exploitables et le statut final avant téléchargement.
- Les limites de volume doivent être configurables et visibles : taille maximale
  du zip, taille décompressée maximale, nombre maximal d'images, taille maximale
  par image, détection zip-bomb, logs par étape et nettoyage automatique du
  stockage temporaire.
- L'export partiel est interdit tant que le traitement n'a pas un statut final
  clair.
- Les seuils par défaut et le mécanisme exact de tâche de fond sont traités dans
  la spec d'orchestration.

## Décisions d'implémentation

- Ne pas reproduire mécaniquement l'orchestration 2025 script par script.
- Préserver les règles métier 2025 qui conditionnent InDesign : nommage des
  en-têtes, emplacement `imageid` / `@pathimg`, encodage CSV, traitement images
  et rapport d'intégrité.
- Généraliser les règles 2025 au multi-onglets par `id_dossier`.
- Ne jamais fonder la logique 2026 sur une position de colonne historique.
- Faire du diagnostic Excel une étape visible et actionnable.
- Faire du mapping une décision utilisateur traçable.
- Faire de l'aperçu CSV une étape de validation avant package.
- Lier toute implémentation des traitements lourds à la spec d'orchestration.
- Unknown : format de stockage et portée des profils de mapping.
- Unknown : format exact du rapport téléchargeable.
- Unknown : liste exacte et noms définitifs des fichiers du package final au-delà
  du minimum décidé.
- Unknown : définition précise de `export testable`.
- Unknown : intégration exacte de l'authentification VPS.
- Unknown : support HEIC réel sur Mac puis VPS.

## Décisions de test

- Seam : diagnostiquer un Excel multi-onglets exploitable avec IDs détectés dans
  les onglets utiles et onglet vide ignoré.
- Seam : refuser un Excel ambigu avec message actionnable.
- Précédent local : `Sircom2.xlsx` doit rester importable quand le fichier réel
  local est présent.
- Précédent local : `Sircom1.xlsx` doit rester refusé quand le fichier réel
  local est présent, notamment à cause de colonnes masquées et formules.
- Seam : générer des Excels synthétiques sans données métier pour tester import,
  refus, mapping, fusion, dates et CSV.
- Seam : vérifier que le CSV final respecte UTF-16 BOM, séparateur virgule, LF,
  en-têtes nettoyés, cellules vides et position `imageid` / `@pathimg`.
- Seam : vérifier qu'une colonne sélectionnée mais entièrement vide est supprimée
  et signalée.
- Seam : vérifier qu'une ligne sans `id_dossier` est supprimée et signalée.
- Seam : vérifier que les champs sensibles restent en texte.
- Seam : vérifier que les dates valides sortent en `dd/mm/yyyy` et que les dates
  invalides sortent vides avec alerte.
- Seam : vérifier le tri région/département confirmé et le repli en ordre Excel
  avec alerte.
- Seam : vérifier le matching images exact, tolérant, fallback par ID, ambigu et
  absent.
- Seam : vérifier l'absence de zip, le zip sans image traitable, les images non
  référencées et les images manquantes comme alertes non bloquantes pour le CSV.
- Seam : vérifier la conversion image JPG, 350 px max, qualité 100, DPI 300,
  fond blanc transparence et orientation EXIF.
- Seam : vérifier que le rapport contient mapping, intégrité, suppressions et
  alertes images.
- Seam : vérifier que le package contient au minimum CSV, images traitées,
  rapport et mapping.

## Passe critique avocat du diable

### Steel-man

Le contrat fonctionnel est solide pour cadrer une V1 : il sépare l'entrée Excel,
le mapping, le CSV InDesign, les images et le rapport, tout en préservant les
règles 2025 qui ont déjà fonctionné dans InDesign. Il corrige aussi plusieurs
tensions dangereuses, notamment `#N/A` remplacé par cellules vides et `B_ID` /
`F_ID` remplacés par `id_dossier` logique.

### Préoccupations

- Résumé : les profils de mapping peuvent devenir dangereux s'ils sont réutilisés
  sur une structure Excel différente.
  Sévérité : Haute, bloquante avant profils persistés. Cadre : pré-mortem et
  cycle de vie des données. Description : le mapping semi-automatique avec profil
  est décidé, mais la portée, la version et les conditions de réutilisation du
  profil restent inconnues. Conséquence : un ancien profil peut mapper une
  colonne homonyme ou déplacée vers un champ final incorrect sans erreur visible.
  Recommandation : lier tout profil à une empreinte de structure et exiger une
  revalidation quand onglets, en-têtes, lettres ou collisions changent.
- Résumé : `export testable` bloque l'export mais reste non défini.
  Sévérité : Haute, bloquante avant package final. Cadre : inversion et chapeau
  blanc. Description : la spec liste `export testable` comme condition de
  blocage, sans critère minimal fermé. Conséquence : l'UI peut bloquer sans
  explication, ou laisser passer un package impossible à valider. Recommandation :
  reprendre les critères minimaux déjà nommés dans les tensions LLM et les
  transformer en checklist d'acceptation du package.
- Résumé : la fidélité au CSV 2025 peut être surinterprétée comme fidélité aux
  colonnes 2025.
  Sévérité : Haute, bloquante avant export CSV. Cadre : inversion. Description :
  le document affirme que le CSV 2025 est une référence de sortie, mais il
  insiste aussi sur ses 80 colonnes et exemples d'en-têtes. Conséquence : un
  agent peut essayer de reproduire la structure 2025 plutôt que le format
  d'encodage, de nommage et de placement des colonnes ajoutées. Recommandation :
  distinguer explicitement `format CSV InDesign` et `liste de colonnes 2025`,
  seule la première étant normative pour 2026.
- Résumé : la compatibilité DSFR/RGAA est mentionnée sans contrat d'écran.
  Sévérité : Moyenne, à surveiller. Cadre : conception UX/API et accessibilité.
  Description : la spec demande des onglets DSFR avec états, aperçu et alertes,
  mais ne définit pas encore les écrans, priorités d'information, libellés ni
  parcours clavier. Conséquence : l'implémentation peut être fonctionnelle mais
  difficile à utiliser ou impossible à auditer RGAA sans reprise importante.
  Recommandation : traiter ce point dans le document design/architecture avec un
  inventaire d'écrans et des états UI observables.
- Résumé : les règles images sont nombreuses et leur priorité en cas de cumul
  n'est pas encore totalement ordonnée.
  Sévérité : Moyenne, à surveiller. Cadre : cas limites. Description : absence
  de zip, zip sans image traitable, images manquantes, images non référencées,
  correspondance tolérante et ambiguïtés sont définies séparément. Conséquence :
  deux anomalies simultanées peuvent produire des messages contradictoires ou une
  mauvaise priorité dans l'interface. Recommandation : définir une matrice de
  priorité des problèmes images et tester les combinaisons réalistes.
- Résumé : le rapport métier est central mais son format exact est encore ouvert.
  Sévérité : Moyenne, à surveiller. Cadre : observabilité et support.
  Description : le contenu minimal du rapport est décrit, mais pas sa forme, sa
  granularité, son audience ni sa stabilité comme artefact de recette.
  Conséquence : le rapport peut être utile au développeur mais insuffisant pour
  le Sircom ou pour justifier les corrections demandées. Recommandation : définir
  un modèle de rapport avec sections fixes, compteurs, listes d'alertes et résumé
  actionnable.

Verdict : livrer avec modifications. La spec fonctionnelle est assez claire pour
préparer le document design/architecture, mais elle ne doit pas être découpée en
tickets d'implémentation tant que `export testable`, les profils de mapping et
le modèle de rapport ne sont pas précisés.

## Matrice connu-inconnu

### Connus connus

- La cible est une interface web autonome pour l'édition Sircom 2026.
- La stack cible est FastAPI avec OpenAPI/Swagger et frontend DSFR/RGAA comme
  référence de conception.
- L'input métier est un Excel multi-onglets uploadé par l'utilisateur.
- La clé métier 2026 est `id_dossier`, sans dépendance à `B_ID` ou `F_ID`.
- L'ensemble des lignes CSV V1 est l'union des `id_dossier` des onglets utiles.
- Le CSV 2025 est une référence de sortie InDesign, pas un input.
- Le CSV final est UTF-16 avec BOM, virgule, LF et cellules vides conservées.
- Le mapping garde la provenance complète et peut sélectionner un sous-ensemble
  de colonnes.
- Les images viennent d'un zip uploadé, à la racine, avec une image principale
  par dossier en V1.
- Le package contient au minimum CSV, images traitées, rapport et mapping.
- Les vrais Excels restent locaux ; les tests reproductibles passent par des
  fichiers synthétiques générables.

### Connus inconnus

- `[^]` Critères exacts de `export testable` et checklist de blocage de l'export.
- `[^]` Portée, stockage, versionnement et invalidation des profils de mapping.
- `[^]` Modèle exact du rapport téléchargeable : sections, formats, compteurs et
  niveau de détail.
- `[~]` Liste finale des fichiers du package et noms exacts des artefacts.
- `[~]` Format précis du dictionnaire de mapping multi-onglets.
- `[~]` Écrans DSFR et comportement accessible des onglets, alertes, aperçu et
  validation.
- `[~]` Disponibilité réelle HEIC/Pillow sur Mac puis VPS.
- `[~]` Niveau de preuve attendu pour valider le package dans InDesign.

### Inconnus connus

- `[^]` La parité 2025 peut pousser un agent à recopier des scripts et positions
  de colonnes au lieu de préserver seulement les règles métier utiles.
- `[^]` Le mapping libre peut masquer des erreurs métier si l'utilisateur valide
  une colonne plausible mais incorrecte.
- `[^]` Le refus strict Excel suppose que le Sircom peut corriger ou régénérer un
  export Démarches Simplifiées assez vite.
- `[~]` Le zip images plat est simple, mais un vrai zip reçu peut contenir des
  dossiers, fichiers parasites ou doublons après normalisation.
- `[~]` L'absence d'images non bloquante facilite l'export CSV, mais peut produire
  un package final frustrant si le rapport ne rend pas le risque très visible.
- `[~]` La référence InDesign 2025 réduit le risque, mais ne prouve pas que le
  gabarit 2026 n'ajoutera aucune contrainte nouvelle.

### Inconnus inconnus

- `[^]` L'Excel 2026 réel peut contenir une structure hybride non couverte par
  les Excels 2024/2025 : onglets répétés, colonnes homonymes utiles, dates
  mixtes, IDs proches ou formules résiduelles.
- `[^]` Une collision de noms CSV après nettoyage peut apparaître seulement après
  mapping ou ajout de provenance multi-onglets, pas au diagnostic initial.
- `[^]` Un nom d'image peut être lisible pour l'utilisateur mais différent après
  normalisation Unicode, casse, extension ou caractères invisibles.
- `[~]` Le rapport peut devenir l'artefact principal de support si le Sircom doit
  demander des corrections aux commanditaires.
- `[~]` Un vrai test InDesign peut révéler que certaines contraintes implicites
  de 2025 n'ont pas été capturées par l'analyse du CSV seul.

Risques prioritaires : `export testable`, stabilité des profils de mapping,
distinction format CSV 2025 vs colonnes 2025, modèle de rapport, preuve InDesign
de bout en bout.

Verdict connu-inconnu : prêt sous conditions. Le contrat fonctionnel est prêt
pour alimenter le document design/architecture, mais les inconnues élevées
doivent être converties en décisions ou en tests avant `/to-tickets`.

## Hors périmètre

- Architecture détaillée backend/frontend.
- Schéma SQLite, worker local, statuts persistés, reprise et purge.
- Authentification de production.
- Conformité DSFR/RGAA déclarée sans audit.
- Gestion de plusieurs images principales par dossier.
- Images dans des sous-dossiers du zip en V1.
- Choix automatique sur correspondance image ambiguë.
- Tolérance forte automatique sur noms d'images partiellement ressemblants.
- Correction automatique globale des nombres, montants, prix ou pourcentages.
- Remise en cause du format CSV InDesign 2025.
- Publication tracker externe.

## Questions ouvertes

- Couplage gabarit InDesign 2026 : confirmer avec le Sircom si le gabarit de
  publipostage 2026 référence les noms 2026 (`id_dossier` et noms nettoyés issus
  du mapping) ou réemploie les noms de champ 2025 (`b_id`, `a_madeinfr`, etc.).
  Dans le second cas, prévoir un adaptateur de noms ou faire adapter le gabarit.
  La fidélité au format 2025 ne couvre pas l'identité des noms de colonnes ; un
  test InDesign sur échantillon reste le contrôle final hors automatisation V1.
- Format de stockage et portée des profils de mapping.
- Format exact du rapport téléchargeable.
- Liste exacte des fichiers du package final au-delà du minimum.
- Définition précise de `export testable`.
- Disponibilité HEIC/Pillow sur Mac puis VPS.
- Intégration de l'authentification sur VPS interne.
- Forme exacte des écrans DSFR et composants UI.
- Format précis du dictionnaire de mapping multi-onglets.
- Matrice de priorité des problèmes images quand plusieurs anomalies sont
  présentes sur le même lot.
- Règles de sécurité d'upload et d'extraction zip, à raccorder à la spec
  d'orchestration.
- Niveau de preuve attendu pour dire que le package est accepté par InDesign.

## Tensions à lever pour implémentation LLM

- `#N/A` vs cellule vide : les décisions intermédiaires `#N/A` sont remplacées
  par Q73. La sortie finale garde des cellules vides ; les absences sont
  seulement signalées dans l'interface et le rapport.
- CSV 2025 input vs output : le CSV 2025 sert de référence de sortie InDesign,
  pas de modèle d'entrée.
- Format CSV 2025 vs colonnes 2025 : le format, l'encodage, les règles de
  nommage et les colonnes ajoutées sont normatifs ; la liste exacte des colonnes
  2025 ne l'est pas pour un Excel 2026 mappé par l'utilisateur.
- `B_ID` / `F_ID` vs `id_dossier` : les lettres historiques ne doivent pas être
  codées en dur. La seule clé métier 2026 est `id_dossier`.
- Colonne `id_dossier` exportée vs renommage 2025 : la colonne d'identifiant
  finale s'appelle `id_dossier`. Les anciennes formes `b_id` ou `f_id` ne sont
  pas normatives pour 2026.
- Ensemble des lignes CSV : utiliser l'union des `id_dossier` non vides des
  onglets utiles. Ne pas choisir arbitrairement le premier onglet comme source de
  vérité.
- Onglet utile vs onglet vide : un onglet vide est ignoré avec information ; un
  onglet non vide sans `id_dossier` bloque l'import.
- Mapping par défaut vs mapping validé : le mapping par défaut sélectionne toutes
  les colonnes des onglets utiles, mais il doit quand même être présenté et
  validé avant export.
- Scripts 2025 vs flux 2026 : les scripts 2025 sont une référence de règles
  métier, pas une architecture à recopier telle quelle.
- Export CSV sans images vs package complet : l'absence d'image ne bloque pas le
  CSV. Le package peut être produit sans images avec alerte forte, sauf si une
  autre règle bloquante s'applique.
- Zip avec sous-dossiers vs zip sans image traitable : la V1 ne traite que les
  images à la racine. Toute image placée dans un sous-dossier est refusée en V1,
  sauf fichiers système explicitement ignorables (`__MACOSX/`, `.DS_Store`). Un
  zip sans image traitable peut laisser possible l'export CSV sans images avec
  alerte forte si les autres critères sont valides.
- Téléchargements séparés vs package requis : les téléchargements séparés sont
  optionnels ; le package zip complet est le livrable obligatoire.
- Mapping libre vs compatibilité InDesign : l'utilisateur choisit les champs,
  mais les noms finaux doivent toujours respecter la règle de nettoyage 2025.
- Refus Excel vs diagnostic : un Excel refusé ne passe pas en transformation,
  mais le diagnostic doit rester exploitable pour corriger le fichier.
- Dev sans auth vs prod avec auth : ne pas construire de logique métier qui
  suppose l'absence durable d'authentification.

## Notes complémentaires

- Le dépôt ne contient pas `docs/agents/issue-tracker.md` ni
  `docs/agents/triage-labels.md`; la spec est donc publiée localement en
  Markdown, conformément à la demande.
- Les fichiers Excel réels restent locaux et non committés.
- Les fichiers synthétiques doivent être générables à la demande et ne pas porter
  de données métier réelles.
- Q5 et Q20 ne figurent pas dans le journal `cuisine-moi` actuel ; la spec
  couvre les décisions présentes de Q0 à Q79.
