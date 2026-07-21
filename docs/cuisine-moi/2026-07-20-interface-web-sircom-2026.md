Interface web Sircom 2026 : notes cuisine-moi
================================================

Date : 2026-07-20 | Objectif : cadrer l'interface web qui rend le Sircom autonome sur import Excel, mapping, images et export InDesign.

## Résumé / décisions clés

- À confirmer : le service doit couvrir l'édition 2026 avec une interface web autonome.
- Décidé : le mapping doit être semi-automatique avec profil réutilisable ; l'app propose un mapping à partir des noms de colonnes, l'utilisateur confirme, puis peut sauvegarder le profil.
- À confirmer : les images seront envoyées dans un zip, dézippées, traitées et renommées selon les règles existantes.
- À confirmer : l'export final doit produire un CSV UTF-16 compatible InDesign.
- Décidé : si l'Excel 2026 contient des dates utiles, elles doivent être traitées selon la règle 2025 et sortir au format `dd/mm/yyyy`.
- Décidé : les Excels réels retrouvés `Sircom1.xlsx` et `Sircom2.xlsx` servent de corpus de non-régression local, tandis que des Excels synthétiques servent à tester les cas contrôlés et reproductibles.
- À cadrer : l'orchestration 2026 doit remplacer l'enchaînement linéaire des scripts 2025 par un pipeline observable, testable et compatible avec des traitements en tâche de fond.

## Journal questions-réponses

### Q0 - Mode de clarification
- Question : confirmer le déroulé de la session `cuisine-moi`.
- Capture : Alex veut répondre aux questions une par une ; ne pas poser de rafale de questions.
- Drapeaux : Aucun.

### Q1 - Modèle de mapping
- Question : veux-tu que l'interface gère le mapping comme un réglage ponctuel par import, ou comme des profils réutilisables ?
- Capture : décision pour un mapping semi-automatique avec profil ; l'app propose un mapping à partir des noms de colonnes, l'utilisateur confirme, puis peut sauvegarder le profil.
- Drapeaux : format de stockage et portée des profils à définir -> Alex / implémentation.

### Q2 - Sélection des champs de sortie
- Question : pour le mapping, est-ce que l'utilisateur doit mapper vers une liste de champs InDesign imposée, ou peut-il créer librement les champs de sortie ?
- Capture : les fichiers peuvent contenir plusieurs onglets et beaucoup de colonnes ; le Sircom n'a pas forcément besoin de tous les champs. L'utilisateur doit pouvoir choisir seulement les champs utiles. Si aucun choix n'est défini, l'outil peut produire par défaut un CSV plat avec tous les champs disponibles. Les noms de colonnes exportés doivent être nettoyés pour InDesign selon les règles du script actuel : minuscules, sans accents, sans caractères spéciaux, 10 caractères maximum. L'app doit garder la correspondance entre le nom nettoyé et la colonne d'origine.
- Drapeaux : stratégie d'aplatissement multi-onglets à définir -> Alex ; format du dictionnaire original vers export InDesign à définir -> implémentation.

### Q3 - Clarification multi-onglets
- Question : comment doit-on transformer un Excel à plusieurs onglets en CSV plat ?
- Capture : Alex n'a pas compris la question et demande de vérifier les scripts existants. Vérification faite : les scripts 2025 préservent parfois tous les onglets au début, mais les traitements métier principaux utilisent surtout la feuille active ou le premier onglet. Il n'existe pas de logique de fusion multi-onglets dans la chaîne actuelle. Pour 2026, hypothèse forte : fusion par identifiant dossier ; l'utilisateur choisit une colonne clé commune, puis l'app fusionne les onglets autour de cette clé, qui sert de clé primaire à tous les onglets du fichier source Excel.
- Drapeaux : confirmer dans le fichier source réel que l'identifiant dossier est présent et stable dans tous les onglets utiles -> Sircom.

### Q4 - Correspondance images
- Question : côté images, quelle doit être la clé de correspondance entre les lignes Excel et les fichiers image dans le zip ?
- Capture : Alex demande de vérifier les scripts, avec souvenir que les images ont un nom de fichier avec extension et qu'elles sont renommées à partir de l'ID dossier. Vérification faite : le script `2-image_id_adder.py` génère une colonne `image-id` depuis `F_ID` au format `dossier-{ID}.jpg`; le script `7-add_pathimg_excel.py` normalise cette valeur en minuscules, sans points ni espaces, puis produit `imageid` et `@pathimg`; le script `10-process-images.py` lit `f_id` et `imageid` depuis `7-add-pathimg.xlsx`, cherche dans le dossier source une image correspondant à `imageid`, puis la traite et l'enregistre sous ce nom. Les commentaires de `10-process-images.py` parlent d'une correspondance depuis le nom réel de l'image uploadée, mais le code effectif ne lit pas directement la colonne photo d'origine à ce stade. Décision provisoire : pour 2026, utiliser le nom original du fichier image pour retrouver l'image dans le zip, puis l'ID dossier pour produire le nom final `dossier-{id-normalise}.jpg` et le champ `@pathimg`.
- Drapeaux : confirmer cette règle avec le fichier 2026 réel et le format du zip -> Sircom.

### Q6 - Images manquantes
- Question : si une image attendue est absente du zip, l'outil doit faire quoi ?
- Capture : décision pour un export non bloquant avec alerte. Le CSV doit être produit même si une image manque. La ligne garde `#N/A` ou un chemin vide pour l'image. Un rapport doit lister précisément les images manquantes afin que le Sircom puisse les demander aux commanditaires.
- Drapeaux : décider si la valeur exportée en absence d'image est `#N/A` ou vide -> implémentation / test InDesign.

### Q7 - Rapport et validation
- Question : le rapport de contrôle doit-il être seulement un rapport technique, ou une vraie page de validation métier avant export ?
- Capture : décision pour les deux. L'interface doit proposer une page de validation métier avant export et produire aussi un rapport téléchargeable.
- Drapeaux : format exact du rapport téléchargeable à définir -> implémentation.

### Q8 - Contenu de l'export
- Question : l'export final doit contenir quoi exactement ?
- Capture : décision pour un package zip complet comme export prioritaire, avec si possible des fichiers téléchargeables séparément. Le package doit contenir le CSV UTF-16, les images renommées et optimisées, le rapport et le mapping utilisé.
- Drapeaux : liste exacte des fichiers du package à figer dans la spécification -> implémentation.

### Q9 - Persistance des lots
- Question : l'app doit-elle garder l'historique des lots traités ?
- Capture : décision pour une session éphémère : l'utilisateur uploade, traite et télécharge ; les données métier ne sont pas gardées après. En revanche, conserver des logs techniques peut être utile pour débuguer si besoin.
- Drapeaux : durée de rétention et contenu exact des logs à définir, avec masquage des données sensibles -> implémentation.

### Q10 - Déploiement cible
- Question : l'interface web doit tourner où ?
- Capture : trajectoire en deux temps. Développement et préproduction sur le Mac d'Alex ; production sur VPS interne. Le prototype doit donc éviter les choix qui bloqueraient une migration serveur.
- Drapeaux : contraintes d'authentification, stockage et exploitation du VPS interne à préciser plus tard -> Sircom / DSI.

### Q11 - Architecture dev/preprod/prod
- Question : pour cette trajectoire, faut-il partir directement sur une app web serveur-ready ?
- Capture : décision pour une architecture serveur-ready dès le départ, mais utilisable en mode hybride sur le Mac d'Alex pour dev et préprod. Cela implique backend API, frontend web, stockage temporaire propre, configuration par environnement, et démarrage local simple.
- Drapeaux : stack technique précise à choisir -> Alex / implémentation.

### Q12 - Stack technique et DSFR
- Question : tu as une préférence de stack technique ?
- Capture : décision pour FastAPI avec Swagger/OpenAPI et frontend simple, ergonomique et efficace. Le frontend doit s'appuyer sur le Design System de l'État : composants DSFR, grille DSFR, espacements DSFR, logique RGAA. Sources locales citées par Alex : `/Users/alex/Claude/design-systems`, `/Users/alex/Claude/design-systems/dsfr/DESIGN.md`, skill `/Users/alex/Claude/.claude/skills/dsfr-components`, exemples `/Users/alex/Claude/projets-heberges/ernie`, `/Users/alex/Claude/projets-heberges/agentic-design-packs`, `/Users/alex/Claude/git-hors-workflow/ay11-pre-audit`. Sources lues pendant la session : `dsfr-components/SKILL.md`, `design-systems/dsfr/DESIGN.md`, `design-systems/dsfr/tokens.yaml`.
- Drapeaux : ne pas revendiquer `conforme DSFR`, `conforme RGAA` ou `prêt pour publication` sans preuve dédiée ; prévoir un audit RGAA/DSFR avant publication -> implémentation.

### Q13 - Authentification
- Question : l'app doit-elle avoir une authentification dès la première version ?
- Capture : décision pour pas d'authentification en dev/préprod sur le Mac d'Alex, à condition de ne pas exposer l'app. En production VPS, un système d'authentification existe et sera précisé plus tard.
- Drapeaux : mode d'intégration de l'authentification VPS à préciser plus tard -> Alex / VPS.

### Q14 - Navigation interface
- Question : tu imagines l'interface comme un assistant étape par étape ou comme des onglets libres ?
- Capture : décision pour des onglets avec état bloquant. La navigation est libre, mais chaque onglet indique son statut et l'export reste bloqué tant que les étapes minimales ne sont pas prêtes.
- Drapeaux : critères exacts de blocage export à définir -> Alex / implémentation.

### Q15 - Critères de blocage export
- Question : qu'est-ce qui doit bloquer l'export ?
- Capture : décision pour un blocage qualité. L'export est bloqué si l'Excel n'est pas importé, si le mapping n'est pas validé, si la colonne ID est absente, si aucune colonne n'est sélectionnée pour l'export, ou si l'export n'est pas testable. Les images manquantes ne bloquent pas et doivent seulement produire des alertes.
- Drapeaux : définir précisément `export testable` dans les critères techniques -> implémentation.

### Q16 - Périmètre de première version
- Question : pour une première version utile, tu veux viser quel périmètre ?
- Capture : Alex ne fixe pas encore le périmètre détaillé, mais demande au minimum l'équivalent fonctionnel des scripts 2025. Vérification des scripts : la parité minimale couvre import Excel, normalisation des vides en `#N/A`, ajout de références de colonnes, génération d'un identifiant image depuis l'ID dossier, nettoyage des en-têtes InDesign, ajout de `imageid` et `@pathimg`, nettoyage du contenu (`<br>`, espaces, colonnes/lignes vides), export CSV UTF-16 avec BOM, traitement images 350 px max / JPEG qualité 100 / 300 DPI, mapping colonnes, vérification d'intégrité, logs et rapport.
- Drapeaux : transformer cette parité 2025 en backlog MVP découpé -> implémentation. Cible long terme à garder : version large avec vraie gestion multi-lots, authentification de production, tableau de bord et historique.

### Q17 - Niveau de clarification images
- Question : le traitement images est-il assez clair ?
- Capture : Alex signale que le traitement images n'a pas été assez interrogé. Réponse de cadrage : les grandes règles sont identifiées, mais il reste des points structurants à verrouiller avant implémentation, notamment nombre d'images par dossier, structure du zip, formats acceptés, collisions de noms et comportement InDesign quand une image manque.
- Drapeaux : approfondir les règles images une par une -> Alex.

### Q18 - Nombre d'images par dossier
- Question : en 2026, est-ce qu'on part sur une seule image principale par dossier ?
- Capture : décision pour une seule image principale par dossier en V1. Si aucun fichier image ne correspond à un dossier, l'app doit produire une alerte explicite pour ce dossier.
- Drapeaux : Aucun.

### Q19 - Structure du zip images
- Question : le zip d'images peut-il contenir des sous-dossiers, ou on impose les images à la racine du zip ?
- Capture : Alex ne se souvient pas et demande de vérifier les scripts. Vérification faite : le script 2025 utilise `os.listdir(source_dir)` et ne descend pas dans les sous-dossiers ; le modèle 2025 est donc un dossier plat d'images. Le script 2025 signale les images référencées mais non trouvées et retourne un succès avec avertissements si au moins une image a été traitée. Décision : pour la V1, images à la racine du zip, absence d'image non bloquante pour le CSV avec alerte. Si le zip contient des images uniquement dans des sous-dossiers, le zip doit être refusé avec un message clair : images attendues à la racine.
- Drapeaux : Aucun.

### Q21 - Formats images acceptés
- Question : quels formats d'images accepte-t-on en V1 ?
- Capture : décision pour reprendre la liste large de 2025 afin d'être permissif. Le résultat final reste toujours converti en JPG. Les erreurs de conversion doivent être signalées dans les logs, le rapport et l'interface de conversion d'images.
- Drapeaux : vérifier les formats réellement supportés par Pillow dans l'environnement cible et documenter les échecs de conversion -> implémentation.

### Q22 - Collisions de noms images
- Question : que fait-on si deux lignes produisent le même nom final `dossier-{id}.jpg` ?
- Capture : décision pour bloquer l'export si l'ID dossier est dupliqué, car l'ID sert de clé primaire et de nommage final.
- Drapeaux : Aucun.

### Q23 - Images non référencées
- Question : si le zip contient des images qui ne sont référencées par aucun dossier Excel, on fait quoi ?
- Capture : décision pour alerte seulement. Les images non référencées sont ignorées pour l'export, mais listées dans l'interface et dans le rapport.
- Drapeaux : Aucun.

### Q24 - Valeurs vides InDesign
- Question : en absence d'image, `@pathimg` doit-il contenir `#N/A` ou rester vide ?
- Capture : décision initiale pour `#N/A` partout, y compris `@pathimg`. Cette décision est remplacée par Q73 après vérification du CSV final 2025 : la sortie CSV finale doit conserver les cellules vides comme le fichier de référence.
- Drapeaux : résolu par Q73.

### Q25 - Correspondance tolérante images
- Question : si l'Excel référence un nom d'image avec une casse ou des espaces différents du fichier dans le zip, l'app doit-elle tenter une correspondance tolérante ?
- Capture : décision pour une correspondance tolérante avec validation. L'app peut ignorer casse, espaces multiples, extension différente ou nom sans extension, mais elle doit signaler la correspondance trouvée dans l'interface et dans le rapport.
- Drapeaux : Aucun.

### Q26 - Ambiguïtés de correspondance images
- Question : si la correspondance tolérante trouve plusieurs images possibles pour un même dossier, que fait l'app ?
- Capture : décision pour ne pas choisir automatiquement. L'app affiche une alerte `plusieurs images possibles` et l'utilisateur doit sélectionner l'image correcte dans l'interface.
- Drapeaux : Aucun.

### Q27 - Niveau de tolérance du matching images
- Question : quand le nom d'image dans l'Excel ne correspond pas exactement au fichier dans le zip, jusqu'où l'app peut proposer une correspondance ?
- Capture : décision pour une tolérance moyenne en automatique : casse différente, espaces en trop, extension différente, nom sans extension, tirets et underscores proches. La tolérance forte, fondée sur une ressemblance partielle du nom, doit seulement produire une suggestion à valider manuellement.
- Drapeaux : Aucun.

### Q28 - Messages d'erreurs images
- Question : pour les erreurs images dans l'interface, tu préfères des messages très techniques ou orientés action ?
- Capture : décision pour deux niveaux. L'interface sert à corriger avec des messages actionnables, formulés pour le métier. Exemple : `Le fichier image est illisible. Remplacez-le ou demandez une nouvelle image.` Les logs servent au debug avec les détails techniques complets.
- Drapeaux : Aucun.

### Q29 - Formats à tester
- Question : pour les tests de conversion images, tu veux qu'on vérifie quels formats au minimum ?
- Capture : décision pour viser le jeu large des formats listés par le script 2025, avec un minimum à tester absolument : JPG, PNG, WEBP, TIFF et HEIC si disponible dans l'environnement.
- Drapeaux : vérifier la disponibilité HEIC et les dépendances Pillow sur Mac Alex puis sur VPS interne -> implémentation.

### Q30 - Audit de couverture images
- Question : relire les scripts de traitement d'images et vérifier s'il reste des trous dans la raquette.
- Capture : scripts relus : `2-image_id_adder.py`, `6-clean_headers_excel.py`, `7-add_pathimg_excel.py`, `8-optimize_content_excel.py`, `9-export_csv_utf16_final.py`, `10-process-images.py`, `11-create_mapping_excel.py`, `12-verify_data_integrity.py` et les validations de `sircom_master_script.py`. Les décisions capturées couvrent bien la plupart du flux 2025 : ID dossier vers `imageid`, `@pathimg`, valeurs manquantes, zip plat, absence d'image non bloquante, images non référencées, formats larges, conversion JPG, logs/rapport/UI, matching tolérant, ambiguïtés manuelles et blocage sur ID dupliqué. Trous restants identifiés : absence complète de zip ou aucune image traitable ; normalisation exacte des IDs pour le nom final ; fallback si l'Excel ne contient pas le nom original du fichier image ; fond blanc pour images transparentes ; orientation EXIF ; nom du dossier d'images dans le package final par rapport au chemin InDesign `/Users/victoria/Documents/export-jpg-resize`.
- Drapeaux : trous métier résolus dans Q31 à Q37 ; restent les vérifications techniques d'environnement.

### Q30bis - Rythme de clarification
- Question : confirmer le rythme de clarification après l'audit des trous images.
- Capture : Alex demande de poser les questions une à une.
- Drapeaux : Aucun.

### Q31 - Absence de zip images
- Question : si aucun zip image n'est fourni, l'app doit-elle quand même permettre l'export CSV ?
- Capture : décision pour autoriser l'export avec alerte forte. Le CSV est produit, mais l'interface signale clairement que le package sera sans images.
- Drapeaux : Aucun.

### Q32 - Zip fourni sans image traitable
- Question : si un zip est fourni mais qu'aucune image n'est traitable, l'app doit-elle permettre l'export CSV ?
- Capture : décision pour autoriser l'export avec alerte forte. Le CSV est généré et le rapport indique `aucune image traitable`.
- Drapeaux : Aucun.

### Q33 - Normalisation des ID images
- Question : pour normaliser l'ID dossier dans le nom final `dossier-{id}.jpg`, on garde exactement la règle 2025 ?
- Capture : décision impérative : garder exactement la règle 2025, sans changement, car InDesign dépend de cette convention. Règle : minuscules, suppression des points, suppression des espaces, conservation des tirets.
- Drapeaux : Aucun.

### Q34 - Fallback image sans nom original
- Question : si l'Excel 2026 ne contient pas de colonne avec le nom original du fichier image, que fait l'app pour retrouver les images ?
- Capture : décision pour valider le fallback par ID dossier quand la colonne `nom original image` est absente. L'app tente d'abord par nom original si disponible ; sinon elle cherche par ID dossier normalisé. Si elle matche par ID, elle le signale dans l'interface et le rapport.
- Drapeaux : Aucun.

### Q35 - Transparence images
- Question : pour les images transparentes (`PNG`, `WEBP`, etc.), on garde la règle 2025 qui ajoute un fond blanc avant conversion JPG ?
- Capture : décision pour conserver le fond blanc, comme en 2025.
- Drapeaux : Aucun.

### Q36 - Orientation EXIF
- Question : faut-il corriger automatiquement l'orientation EXIF des photos avant redimensionnement ?
- Capture : décision pour appliquer automatiquement l'orientation EXIF avant conversion JPG.
- Drapeaux : Aucun.

### Q37 - Nom du dossier images exportées
- Question : dans le package final, le dossier des images traitées doit s'appeler comment ?
- Capture : décision pour `export-jpg-resize/`, comme l'année dernière, parce que c'est le nom attendu par le chemin InDesign `/Users/victoria/Documents/export-jpg-resize/...`.
- Drapeaux : Aucun.

### Q38 - Nom du zip images en entrée
- Question : le zip images uploadé en entrée doit-il avoir un nom précis, par exemple `images.zip`, ou le nom est-il libre ?
- Capture : décision pour un nom libre. L'app accepte n'importe quel fichier `.zip`; elle valide le contenu plutôt que le nom. Contraintes associées : un seul zip images par lot, images attendues à la racine, sous-dossiers refusés, nom original du zip conservé dans les logs et le rapport.
- Drapeaux : Aucun.

### Q39 - Source images du lot
- Question : pour l'application web 2026, la source images du lot est-elle le zip uploadé ?
- Capture : décision confirmée. Le zip uploadé est la source images du lot pour l'application web. Il n'y a pas de répertoire source fixe à configurer dans l'app pour les images métier.
- Drapeaux : Aucun.

### Q40 - Modèle multi-onglets pour le CSV final
- Question : pour 2026, faut-il une feuille principale qui définit la liste des dossiers exportés ?
- Capture : réponse négative. Le besoin connu à ce stade est plus générique : l'Excel source aura plusieurs onglets, chaque onglet aura plusieurs colonnes, mais le fichier type n'est pas encore disponible. La cible concrète est le CSV final InDesign, qui doit ressembler au fichier 2025 `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`.
- Drapeaux : analyser le CSV 2025 de référence pour cadrer le contrat de sortie -> implémentation.

### Q41 - Analyse du CSV 2025 de référence
- Question : que montre le CSV 2025 pointé comme référence de sortie ?
- Capture : le fichier de référence est lisible en UTF-16 little-endian, avec séparateur virgule. Il contient 10 lignes dont 9 lignes de données et 80 colonnes. Les en-têtes commencent par `a_madeinfr`, `b_id`, `imageid`, `@pathimg`, puis des champs source nettoyés et tronqués. Ce CSV ressemble à une ancienne structure large plutôt qu'à la structure active documentée de 25 colonnes avec `f_id`.
- Drapeaux : résolu par Q42 ; la forme large sert de référence, mais la cible 2026 reste un CSV plat construit depuis le mapping utilisateur.

### Q42 - Contrat général XLSX vers CSV
- Question : faut-il traiter le CSV 2025 comme un profil InDesign par défaut, modifiable par mapping utilisateur ?
- Capture : clarification d'Alex : l'objectif n'est pas de figer une forme de colonnes à ce stade, mais de prendre un Excel multi-onglets, de le convertir en CSV plat UTF-16, et d'appliquer tous les traitements nécessaires issus des différents scripts pour aboutir au livrable final InDesign.
- Drapeaux : préciser la règle d'aplatissement des onglets en lignes et colonnes du CSV -> Alex.

### Q43 - Rôle du CSV 2025 de référence
- Question : clarifier le statut du CSV 2025 dans le cadrage 2026.
- Capture : correction d'Alex : le CSV de référence est l'output attendu, pas l'input. Il sert à comprendre la forme, l'encodage et les contraintes du livrable final InDesign. L'input 2026 reste un fichier Excel multi-onglets uploadé par l'utilisateur.
- Drapeaux : Aucun.

### Q44 - Colonnes exportées depuis un Excel multi-onglets
- Question : confirmer la logique d'export des colonnes quand l'Excel source contient plusieurs onglets.
- Capture : correction d'Alex : si aucun mapping n'est défini, toutes les colonnes de tous les onglets sont mises à plat dans le CSV final, avec le renommage compatible InDesign. Si un mapping est défini, l'utilisateur peut choisir seulement quelques champs de chaque onglet pour l'export final.
- Drapeaux : préciser comment rattacher les lignes des différents onglets entre elles dans le CSV final -> Alex.

### Q45 - Clé primaire d'aplatissement
- Question : comment associer les lignes des différents onglets entre elles dans le CSV final ?
- Capture : décision confirmée. Une ligne du CSV final se construit par la clé primaire `id_dossier`. Cette clé permet d'associer les lignes des différents onglets et de produire la fusion à plat du mapping dans le CSV final.
- Drapeaux : Aucun.

### Q46 - Vocabulaire ID dans les onglets
- Question : que signifie la présence de `id_dossier` dans les différents onglets ?
- Capture : clarification d'Alex : chaque onglet Excel contient une colonne `id_dossier`. Il y a plusieurs `id_dossier` dans les différents onglets du classeur Excel. La fusion à plat utilise cette colonne commune pour rattacher les champs des onglets au même dossier.
- Drapeaux : résolu par Q50.

### Q47 - Doublon d'ID dans un même onglet
- Question : que faire si le même `id_dossier` apparaît deux fois dans un même onglet ?
- Capture : correction d'Alex : ce cas n'est pas attendu comme scénario métier. Les lignes et colonnes vides ont été renseignées en `N/C`, donc l'app ne doit pas construire le modèle autour de ce cas. À conserver au plus comme validation technique d'intégrité si un fichier réel contredit cette hypothèse.
- Drapeaux : résolu par Q48.

### Q48 - Normalisation de `N/C`
- Question : dans le CSV final, `N/C` doit-il rester `N/C` ou être converti en `#N/A` ?
- Capture : décision initiale pour convertir `N/C` en `#N/A`. Cette décision est remplacée par Q73 : les valeurs vides ou assimilées à une absence doivent sortir en cellule vide dans le CSV final, comme dans le CSV 2025 de référence.
- Drapeaux : résolu par Q73.

### Q49 - Nomenclature des cellules vides
- Question : quelle nomenclature unique utiliser pour les cellules vides dans le CSV final, en se fondant sur le CSV 2025 de référence ?
- Capture : vérification du fichier `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv` : 10 lignes, 9 lignes de données, 80 colonnes, 55 cellules vides, 0 cellule `#N/A`, 0 cellule `N/C`. Le CSV de référence contredit donc la décision précédente `#N/A` partout pour les vides.
- Drapeaux : résolu par Q73 ; la règle 2026 revient à la fidélité au CSV 2025 avec cellules vides dans la sortie finale.

### Q50 - ID absent dans certains onglets
- Question : si un `id_dossier` existe dans un onglet mais pas dans un autre, faut-il garder la ligne et remplir les champs manquants avec `#N/A` ?
- Capture : décision confirmée pour conserver la ligne. La valeur de remplacement `#N/A` est remplacée par Q73 : les champs issus de l'onglet absent restent vides dans le CSV final, même si ce cas ne devrait normalement pas se produire.
- Drapeaux : résolu par Q73.

### Q51 - Règle finale des valeurs absentes
- Question : faut-il verrouiller `#N/A` partout pour toute valeur vide ou absente dans le CSV final ?
- Capture : décision initiale pour `#N/A` partout. Cette décision est remplacée par Q73 après analyse du CSV 2025 de référence.
- Drapeaux : résolu par Q73.

### Q52 - Règle de renommage des colonnes InDesign
- Question : pour le renommage des colonnes InDesign, faut-il garder exactement la règle 2025 : minuscules, sans accents, suppression des caractères spéciaux, longueur maximale 10 caractères ?
- Capture : décision impérative. Garder exactement la règle 2025, car InDesign casse le publipostage si cette convention n'est pas respectée. Correction importante : la règle 2025 ajoute d'abord la référence de colonne Excel (`A_`, `B_`, `AA_`, etc.) au nom original, puis applique le nettoyage InDesign : minuscules, sans accents, suppression des caractères spéciaux, longueur maximale 10 caractères. Preuve sur le CSV 2025 : 78 en-têtes sur 80 suivent cette forme, par exemple `a_madeinfr`, `b_id`, `c_email`; les exceptions ajoutées sont `imageid` et `@pathimg`.
- Drapeaux : Aucun.

### Q53 - Mapping interne multi-onglets
- Question : pour 2026, le mapping interne doit-il conserver la provenance complète `onglet + lettre colonne + nom original`, tandis que le CSV final garde seulement le nom InDesign nettoyé en 10 caractères ?
- Capture : décision confirmée. Le mapping interne 2026 doit conserver la provenance complète, en s'inspirant de `livrables-miweb-2025/livrables-miweb-1-2025/mapping_excel_csv.md` et `livrables-miweb-2025/livrables-miweb-1-2025/structure_csv_analysis.md`. Le modèle 2025 documente la correspondance entre référence Excel, nom complet Excel, nom CSV InDesign, description/type, champs prioritaires et champs ajoutés `imageid` / `@pathimg`. En 2026, ce modèle doit être étendu au multi-onglets avec une provenance d'onglet source.
- Drapeaux : adapter le format 2025 à un Excel multi-onglets en ajoutant l'onglet source -> implémentation.

### Q54 - Ordre des colonnes du CSV final
- Question : pour l'ordre des colonnes dans le CSV final, faut-il suivre l'ordre du classeur Excel : onglets dans leur ordre, colonnes dans leur ordre, avec `imageid` et `@pathimg` placés juste après `id_dossier` ?
- Capture : décision confirmée. Le CSV final suit l'ordre du classeur Excel : onglets dans leur ordre, colonnes dans leur ordre. Les colonnes ajoutées `imageid` et `@pathimg` sont placées juste après `id_dossier`.
- Drapeaux : Aucun.

### Q55 - Export de l'ID en 2025
- Question : en 2025, combien de colonnes ID étaient exportées dans le CSV final et où étaient placées `imageid` et `@pathimg` ?
- Capture : vérification faite dans le CSV final 2025 et les scripts. Le CSV de référence contient un seul champ ID métier exporté, `b_id`, en colonne 2, puis `imageid` en colonne 3 et `@pathimg` en colonne 4. Les scripts ajoutent `image-id` juste après la colonne ID source, puis le nettoyage transforme ce champ en `imageid`, et le script suivant insère `@pathimg` juste après `imageid`. Nuance : le CSV de référence documente l'ancienne structure avec `B_ID`, tandis que le script actuel adapté cherche `F_ID`.
- Drapeaux : résolu par Q57.

### Q56 - Référence logique `id_dossier`
- Question : faut-il considérer `B_ID` ou `F_ID` comme référence fixe pour 2026 ?
- Capture : correction d'Alex : on ne sait pas encore si l'ID sera en colonne B, F ou ailleurs dans l'Excel 2026. La référence métier et technique est `id_dossier`, qui sert de clé primaire. Les lettres de colonne observées en 2025 sont seulement des positions source, pas des constantes à coder en dur.
- Drapeaux : Aucun.

### Q57 - Colonne ID exportée
- Question : dans le CSV final, faut-il exporter une seule colonne `id_dossier` de référence, même si elle existe dans plusieurs onglets ?
- Capture : décision confirmée. Le CSV final exporte une seule colonne `id_dossier` de référence. Les colonnes `id_dossier` présentes dans les autres onglets servent à la fusion interne et ne sont pas répétées dans le CSV final.
- Drapeaux : Aucun.

### Q58 - Tri des lignes du CSV final
- Question : pour le tri des lignes du CSV final, faut-il conserver l'ordre métier déjà présent dans l'Excel, sans retrier automatiquement, sauf demande explicite ?
- Capture : décision ajustée. Le principe 2026 est de conserver le tri métier attendu, avec un tri par région puis département quand les colonnes correspondantes sont disponibles. Les colonnes pouvant changer, l'interface doit proposer les colonnes de tri détectées et faire confirmer le tri par l'utilisateur.
- Drapeaux : préciser le comportement si les colonnes région ou département ne sont pas détectées -> Alex.

### Q59 - Repli si colonnes de tri absentes
- Question : si l'app ne détecte pas clairement les colonnes région ou département, faut-il garder l'ordre Excel avec une alerte non bloquante ?
- Capture : décision confirmée. L'export reste possible. L'ordre Excel est conservé et le rapport signale que le tri région/département n'a pas été appliqué.
- Drapeaux : Aucun.

### Q60 - Sauts de ligne dans les cellules
- Question : pour les sauts de ligne dans les cellules, faut-il garder la règle 2025 et remplacer les retours ligne par `<br>` dans le CSV final ?
- Capture : décision confirmée. Les retours ligne dans les cellules sont convertis en `<br>` dans le CSV final.
- Drapeaux : Aucun.

### Q61 - Nettoyage des espaces dans les cellules
- Question : faut-il garder le nettoyage 2025 des espaces dans les cellules : trim début/fin et remplacement des espaces multiples par un seul espace ?
- Capture : décision confirmée. Les cellules exportées sont nettoyées avec suppression des espaces en début et fin, puis réduction des espaces multiples à un seul espace.
- Drapeaux : Aucun.

### Q62 - Colonnes entièrement vides
- Question : pour les colonnes entièrement vides après fusion/mapping, faut-il les supprimer du CSV final comme en 2025, ou les garder avec `#N/A` partout ?
- Capture : décision confirmée. Les colonnes entièrement vides après traitement sont supprimées du CSV final, comme en 2025.
- Drapeaux : résolu par Q63.

### Q63 - Colonne sélectionnée mais vide partout
- Question : si l'utilisateur sélectionne explicitement une colonne dans le mapping, mais que cette colonne est vide partout après traitement, faut-il la supprimer ou la garder avec `#N/A` partout ?
- Capture : décision confirmée. La colonne est supprimée si elle est vide partout, même si elle avait été sélectionnée dans le mapping.
- Drapeaux : Aucun.

### Q64 - Lignes sans `id_dossier`
- Question : pour les lignes sans `id_dossier`, faut-il garder la règle 2025 : supprimer la ligne et le signaler dans le rapport ?
- Capture : décision confirmée. Les lignes sans `id_dossier` sont supprimées du CSV final et signalées dans le rapport.
- Drapeaux : Aucun.

### Q65 - Format CSV exact
- Question : faut-il verrouiller le format CSV exact de 2025 : UTF-16 avec BOM, séparateur virgule, saut de ligne LF, guillemets automatiques seulement si nécessaire ?
- Capture : décision impérative. Le format CSV final doit respecter exactement ces contraintes pour InDesign : UTF-16 avec BOM, séparateur virgule, saut de ligne LF, guillemets automatiques seulement si nécessaire.
- Drapeaux : Aucun.

### Q66 - Fidélité au format de sortie 2025
- Question : pour les valeurs numériques et identifiants, faut-il convertir tout en texte dans le CSV final afin d'éviter les `.0`, les notations scientifiques et les pertes de zéros initiaux ?
- Capture : correction d'Alex : la sortie 2026 doit impérativement avoir le même format que la sortie 2025 de référence `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`. Vérification structurelle : ce CSV a 80 en-têtes, 9 lignes de données, `a_madeinfr`, `b_id`, `imageid`, `@pathimg` en tête, UTF-16 little-endian avec LF et sans CRLF. Limite observée : certaines valeurs non-ID contiennent encore des formes comme `.0` ou notation scientifique ; il ne faut donc pas inventer une correction globale non demandée sans test InDesign.
- Drapeaux : résolu par Q67.

### Q67 - Protection texte des champs sensibles
- Question : faut-il préserver en texte les champs sensibles pour éviter les formats Excel/Pandas cassés comme `.0`, notation scientifique ou perte de zéros initiaux ?
- Capture : décision confirmée. Garder le format CSV InDesign 2025, mais améliorer la robustesse en préservant en texte les champs sensibles : `id_dossier`, SIRET, téléphone, code postal, département et codes administratifs. Ne pas modifier automatiquement les prix, pourcentages ou montants sans règle explicite.
- Drapeaux : Aucun.

### Q68 - Aperçu avant export
- Question : faut-il prévoir un aperçu avant export dans l'interface avec en-têtes finaux, premières lignes, colonnes supprimées, lignes supprimées et alertes ?
- Capture : décision confirmée. L'interface doit proposer un aperçu avant export avec les en-têtes finaux InDesign, les premières lignes, les colonnes supprimées, les lignes supprimées et les alertes.
- Drapeaux : Aucun.

### Q69 - Mapping complet dans le rapport
- Question : le rapport d'export doit-il inclure le mapping complet utilisé : onglet source, lettre colonne, nom original, nom CSV final, statut exporté ou supprimé ?
- Capture : décision confirmée. Le rapport d'export doit inclure le mapping complet utilisé, avec onglet source, lettre colonne, nom original, nom CSV final et statut exporté ou supprimé.
- Drapeaux : Aucun.

### Q70 - Vérification d'intégrité dans le rapport
- Question : faut-il inclure dans le rapport une vérification d'intégrité type 2025 : nombre d'IDs source, nombre de lignes CSV, IDs supprimés faute d'`id_dossier`, IDs présents dans certains onglets mais absents d'autres, et alertes images ?
- Capture : décision confirmée. Le rapport doit inclure une vérification d'intégrité adaptée au multi-onglets : nombre d'IDs source, nombre de lignes CSV, lignes supprimées faute d'`id_dossier`, IDs présents dans certains onglets mais absents d'autres, colonnes supprimées et alertes images.
- Drapeaux : Aucun.

### Q71 - Logs 2025 comme référence
- Question : utiliser les logs 2025 de `livrables-miweb-2025/livrables-miweb-1-2025/logs` comme référence informative pour les logs 2026 ?
- Capture : information ajoutée par Alex. Les logs 2025 contiennent un rapport de traitement, des logs de chaîne Sircom et des logs images. Structure utile à reprendre : informations générales, statistiques d'exécution, étapes exécutées, fichiers créés, résultat final, paramètres images, correspondances CSV/images, erreurs et résumé. Contrainte 2026 : distinguer logs techniques détaillés et rapport métier, en évitant d'exposer inutilement les données personnelles ou contenus métier dans l'interface.
- Drapeaux : Aucun.

### Q72 - Couverture des scripts 2025
- Question : a-t-on bien questionné les logiques métier de l'intégralité des scripts `scripts-2025/` de 0 à 12 ?
- Capture : verdict de couverture. L'inventaire local contient 14 fichiers Python : l'utilitaire amont `0-extract_departement_to_sircom.py`, les scripts de chaîne `0-si-cellule-vide-na.py` à `12-verify_data_integrity.py`, et le master racine `sircom_master_script.py`. Les décisions capturées couvrent les logiques métier de la chaîne 0 à 12 : extraction/import Excel, normalisation des vides, préfixe lettre colonne, ID image, fusion à plat par `id_dossier`, tri région/département, dates, livrable Excel, nettoyage des en-têtes, `@pathimg`, optimisation contenu, export CSV UTF-16, traitement images, mapping, vérification d'intégrité, logs et rapport. Aucun trou métier majeur identifié à ce stade ; les trous restants sont liés au vrai fichier Excel 2026, aux tests d'environnement et à l'implémentation.
- Drapeaux : Aucun.

### Q73 - Retour à la règle CSV 2025 pour les valeurs vides
- Question : faut-il réduire le risque InDesign en conservant la règle observée dans le CSV final 2025 pour les cellules vides ?
- Capture : décision corrigée. Pour réduire le risque InDesign, la sortie CSV finale 2026 doit conserver strictement la règle observée dans `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv` : les valeurs vides ou absentes sortent en cellule vide, pas en `#N/A`. Cela remplace les décisions Q24, Q48, Q50 et Q51 sur `#N/A` dans le CSV final. Les absences restent visibles dans l'interface et le rapport.
- Drapeaux : Aucun.

### Q74 - Risque gabarit InDesign 2026
- Question : le gabarit InDesign 2026 reste-t-il un risque si le CSV final conserve strictement le format de sortie 2025 ?
- Capture : correction d'Alex. Le CSV de l'année dernière a été réimporté dans InDesign sans problème. Le risque est donc fortement réduit si l'output 2026 conserve strictement le format du fichier de référence `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`.
- Drapeaux : prévoir un test de non-régression sur les caractéristiques du CSV 2025 de référence -> implémentation.

### Q75 - Réduction du risque gros volumes
- Question : comment réduire le risque `zip lourd`, `beaucoup d'images` et `timeout serveur` ?
- Capture : recommandation technique à confirmer. Réduire le risque par des limites configurables et visibles : taille maximale du zip, taille décompressée maximale, nombre maximal d'images, taille maximale par image, détection zip-bomb, traitement en tâche de fond avec progression, logs par étape, nettoyage automatique du stockage temporaire, et export partiel interdit tant que le traitement n'a pas un statut final clair. En local Mac comme sur VPS, ces limites doivent être en variables d'environnement.
- Drapeaux : fixer les seuils de volume par défaut pour la V1 -> Alex / implémentation.

### Q76 - Traitement des dates
- Question : si l'Excel 2026 contient des dates importantes, faut-il les traiter ou seulement signaler leur présence ?
- Capture : décision d'Alex. Les dates doivent être traitées si elles sont présentes. Règle à reprendre : l'ancien script 2025 `4-changer-date-format.py` convertissait les colonnes dates au format français `dd/mm/yyyy`. Le script actif `scripts-2025/4-changer-date-format.py` ne traite plus de dates uniquement parce que la structure 2025 active n'en contenait plus aux positions prévues. Pour 2026, l'interface doit détecter ou faire confirmer les colonnes dates dans le mapping, convertir les valeurs valides en `dd/mm/yyyy`, signaler les valeurs invalides dans l'interface et le rapport, et conserver la fidélité du CSV final 2025 : les valeurs absentes ou non convertibles sortent en cellule vide, pas en `#N/A`.
- Drapeaux : tester la détection et la conversion des dates sur le jeu Excel synthétique puis sur le vrai fichier 2026 -> implémentation.

### Q77 - Exécution des gros traitements
- Question : pour les gros zip et traitements images, faut-il valider une exécution en tâche de fond avec progression, jamais dans une requête HTTP bloquante ?
- Capture : décision confirmée par Alex. Les traitements lourds doivent s'exécuter en tâche de fond avec barre de progression. Le frontend doit afficher l'état du traitement, les étapes réalisées, les erreurs métier exploitables et le statut final avant téléchargement. Le backend ne doit pas faire dépendre la conversion complète d'une requête HTTP longue.
- Drapeaux : fixer les seuils de volume par défaut pour la V1 et choisir le mécanisme technique de file/tâche de fond compatible Mac local puis VPS -> implémentation.

### Q78 - Excel réel avec structure ambiguë
- Question : pour un Excel réel avec cellules fusionnées, en-têtes sur plusieurs lignes, colonnes masquées ou formules, faut-il refuser l'import ou importer partiellement avec alertes ?
- Capture : décision d'Alex. La posture la plus prudente est de refuser l'import de l'Excel et d'expliquer pourquoi. Pour la V1, l'application doit détecter les structures qui rendent l'interprétation ambiguë ou non fiable : cellules fusionnées, en-têtes sur plusieurs lignes, colonnes masquées, formules ou structure empêchant d'identifier proprement les en-têtes et `id_dossier`. Le message doit être clair, actionnable et indiquer ce que le Sircom doit corriger dans le fichier.
- Drapeaux : définir les contrôles techniques exacts d'analyse Excel et les messages d'erreur métier -> implémentation.

### Q79 - Corpus de validation Excel
- Question : comment utiliser les Excels input 2024/2025 retrouvés et les futurs Excels synthétiques dans la validation de l'application ?
- Capture : Alex précise que l'idée est de s'en servir pour vérifier que l'application fonctionne comme prévu et pour constituer des fichiers Excel synthétiques de tests. Vérification locale faite le 2026-07-21 : `livrables-miweb-2025/Sircom1.xlsx` ressemble à l'ancien input mono-onglet large, avec ID en `B:ID`, colonnes masquées et formules ; avec la règle Q78, il est refusé en V1. `livrables-miweb-2025/Sircom2.xlsx` est un input multi-onglets exploitable : onglets `Dossiers`, `Etablissements`, `Avis`, `Composition`, IDs détectés dans les onglets utiles, onglet `Avis` vide ignoré. Décision pratique : les fichiers réels restent locaux et non committés ; ils servent de non-régression structurelle quand présents. Les fichiers synthétiques doivent être générables à la demande pour couvrir les scénarios acceptés/refusés sans données métier.
- Drapeaux : compléter les fixtures synthétiques avec des scénarios de mapping, CSV, images et package final -> implémentation.

### Q80 - Besoin de cadrage orchestration
- Question : est-il utile de cuisiner l'orchestration des traitements plutôt que seulement les règles de transformation ?
- Capture : oui, c'est utile et probablement nécessaire. La chaîne 2025 orchestre des scripts séquentiels avec fichiers intermédiaires. Pour 2026, l'application devra exposer des états visibles, relancer ou reprendre proprement certaines étapes, distinguer tâches rapides et traitements lourds, produire un rapport cohérent, et éviter qu'une requête HTTP longue porte tout le traitement. L'orchestration devient donc un sujet produit et technique, pas seulement un détail d'implémentation.
- Drapeaux : choisir le modèle d'orchestration cible V1 -> Alex / implémentation.

### Q81 - Rythme de cadrage orchestration
- Question : faut-il continuer le cadrage orchestration avec une seule question à la fois ?
- Capture : Alex demande explicitement de poser les questions une à une.
- Drapeaux : Aucun.

### Q82 - Modèle d'orchestration V1
- Question : pour la V1, faut-il partir sur un pipeline typé avec états persistés plutôt qu'un pipeline linéaire simple ou un moteur de tâches complet ?
- Capture : décision pour un pipeline typé avec états persistés. Chaque étape doit avoir un statut, des inputs/outputs, des warnings, des artefacts et des logs. La motivation est la robustesse, la lisibilité UI et la testabilité, avec un coût jugé modéré.
- Drapeaux : choisir le support de persistance de l'état du pipeline -> Alex / implémentation.

### Q83 - Persistance de l'état du pipeline
- Question : pour stocker l'état des lots, étapes, warnings, artefacts et logs, faut-il utiliser fichiers JSON, SQLite local ou une base serveur dès la V1 ?
- Capture : décision pour SQLite local. Les fichiers lourds restent à stocker dans un dossier d'artefacts par lot, tandis que SQLite porte l'état structuré du pipeline.
- Drapeaux : définir la granularité des étapes visibles et persistées dans le pipeline -> Alex / implémentation.

### Q84 - Étapes visibles du pipeline
- Question : faut-il exposer des étapes larges, des étapes métier détaillées ou des étapes calquées sur les 13 scripts 2025 ?
- Capture : décision pour des étapes métier détaillées : `upload_excel`, `diagnostic_excel`, `mapping`, `fusion_multi_onglets`, `normalisation_contenu`, `previsualisation_csv`, `upload_images`, `traitement_images`, `package_final`. Ce découpage est plus lisible pour l'utilisateur et pour les tests, sans coupler l'orchestration web aux scripts historiques. Les libellés UI restent en français ; les identifiants techniques restent sans accents.
- Drapeaux : définir le vocabulaire de statut des étapes -> Alex / implémentation.

### Q85 - Statuts des étapes
- Question : faut-il utiliser des statuts simples, des statuts métier complets, ou des statuts techniques avec sévérité séparée ?
- Capture : décision pour des statuts métier complets, mais en français côté interface. Liste cible : `non démarrée`, `prête`, `en cours`, `action requise`, `bloquée`, `terminée`, `terminée avec alertes`, `échouée`, `ignorée`, `annulée`. Pour l'implémentation, prévoir des identifiants internes stables sans accents, par exemple `non_demarre`, `pret`, `en_cours`, `action_requise`, `bloque`, `termine`, `termine_avec_alertes`, `echoue`, `ignore`, `annule`, avec libellés UI en français.
- Drapeaux : définir quelles transitions de statut sont autorisées entre étapes -> implémentation.

### Q86 - Déclenchement des étapes
- Question : faut-il lancer tout le pipeline automatiquement après upload, demander une action manuelle à chaque étape, ou adopter un mode semi-automatique avec validations ?
- Capture : décision pour un pipeline semi-automatique avec validations. L'application avance seule sur les étapes sûres, mais demande confirmation pour les points sensibles : `mapping`, tri, aperçu CSV et package final.
- Drapeaux : choisir le mécanisme technique de tâche de fond compatible Mac local puis VPS -> Alex / implémentation.

### Q87 - Mécanisme de tâche de fond V1
- Question : pour les traitements de fond en V1, faut-il utiliser `BackgroundTasks` FastAPI, un worker local intégré avec file SQLite, ou Celery/RQ avec Redis ?
- Capture : décision pour un worker local intégré avec file SQLite. Le choix vise un mécanisme léger, testable, compatible avec le Mac local et migrable plus tard sans introduire Redis dès le MVP.
- Drapeaux : définir les règles de relance, reprise et annulation des étapes -> Alex / implémentation.

### Q88 - Règle de reprise après erreur
- Question : en V1, faut-il relancer tout le lot depuis le début, reprendre depuis l'étape échouée, ou permettre une relance fine par sous-tâche ?
- Capture : décision pour relancer depuis l'étape échouée, avec invalidation automatique des étapes suivantes. Cela évite de refaire tout le lot quand une correction locale suffit, sans introduire une relance fine trop complexe pour la V1.
- Drapeaux : décider si l'utilisateur peut annuler un traitement en cours -> Alex / implémentation.

### Q89 - Annulation des traitements
- Question : en V1, faut-il ne pas permettre l'annulation, permettre une annulation coopérative entre sous-étapes, ou forcer une annulation immédiate ?
- Capture : décision pour une annulation coopérative entre sous-étapes. L'utilisateur demande l'arrêt ; le worker termine l'opération courante, arrête avant la sous-étape suivante, puis marque le lot `annulé`.
- Drapeaux : fixer les seuils de volume par défaut pour la V1 -> Alex / implémentation.

### Q90 - Seuils de volume V1
- Question : quels seuils par défaut retenir en V1 pour éviter zip trop lourd, zip-bomb, trop d'images ou fichiers impossibles à traiter ?
- Capture : décision pour des seuils confortables configurables par variables d'environnement : Excel 50 Mo, zip images 1 Go, 1500 images, 50 Mo par image, taille décompressée maximale 3 Go. Ces seuils sont jugés plus réalistes pour des photos, avec contrepartie d'un suivi disque sérieux.
- Drapeaux : définir le schéma minimal SQLite de l'orchestration -> implémentation.

### Q91 - Schéma SQLite d'orchestration
- Question : pour l'orchestration SQLite, faut-il un schéma minimal, un schéma opérationnel ou un schéma complet métier ?
- Capture : décision pour un schéma opérationnel : `lots`, `etapes`, `jobs`, `artefacts`, `evenements`, `problemes`. Ce schéma est plus propre pour représenter les statuts, la file worker, les alertes métier et l'historique sans aller trop tôt vers un modèle métier complet.
- Drapeaux : définir la politique de conservation et nettoyage des lots, artefacts et logs -> Alex / implémentation.

### Q92 - Conservation et suppression des lots
- Question : combien de temps l'application doit-elle conserver les données uploadées, artefacts générés et logs de lot ?
- Capture : décision pour une conservation courte de 7 jours par défaut, configurable par variable d'environnement, avec un bouton de suppression manuelle immédiate du lot. Le choix équilibre reprise/debug local et limitation de l'accumulation de données métier.
- Drapeaux : définir ce qui reste éventuellement après suppression manuelle d'un lot -> Alex / implémentation.

### Q93 - Purge après suppression manuelle
- Question : après suppression manuelle d'un lot, faut-il tout purger, garder une trace technique anonymisée, ou faire seulement une suppression logique ?
- Capture : décision pour une purge métier avec trace technique anonymisée. L'application supprime uploads, artefacts, rapports et valeurs métier ; elle conserve seulement date, statut final, durées, tailles, compteurs et erreurs techniques sans contenu sensible.
- Drapeaux : définir le suivi disque visible et les alertes de stockage -> Alex / implémentation.

### Q94 - Suivi disque visible
- Question : faut-il limiter le suivi disque aux logs, afficher seulement un indicateur par lot, ou afficher un indicateur global et par lot ?
- Capture : décision pour un indicateur de stockage global et par lot. L'interface doit afficher l'espace utilisé total, l'espace libre, les lots les plus lourds, la taille par lot, la date d'expiration et une alerte si un seuil disque est approché.
- Drapeaux : définir l'affichage des problèmes, alertes métier et logs techniques -> Alex / implémentation.

### Q95 - Problèmes métier et logs techniques
- Question : faut-il afficher tous les messages dans un journal unique, séparer les problèmes structurés par étape des logs techniques, ou construire un tableau de bord complet d'observabilité ?
- Capture : décision pour des problèmes structurés par étape et des logs techniques séparés. L'interface affiche les alertes actionnables pour le Sircom ; les logs techniques restent disponibles pour le debug.
- Drapeaux : définir les niveaux de sévérité des problèmes visibles côté métier -> Alex / implémentation.

### Q96 - Sévérité des problèmes métier
- Question : quels niveaux de sévérité utiliser pour les problèmes visibles côté métier ?
- Capture : décision pour trois niveaux : `bloquant`, `alerte`, `information`. `bloquant` empêche de continuer tant qu'une correction n'est pas faite ; `alerte` signale un point non bloquant à valider ou traiter ; `information` documente un constat utile sans action obligatoire.
- Drapeaux : définir les transitions autorisées entre statuts et les messages d'erreur Excel sale -> implémentation.

### Q97 - Priorité restante d'orchestration
- Question : faut-il cadrer d'abord les transitions de statut, les messages d'erreur Excel sale, ou arrêter le cadrage orchestration pour passer à l'implémentation ?
- Capture : décision pour cadrer d'abord les messages d'erreur Excel sale. Ce sujet est prioritaire car il touche directement l'expérience d'upload Sircom et s'appuie sur les vrais fichiers `Sircom1.xlsx` et `Sircom2.xlsx`.
- Drapeaux : définir le format des messages d'erreur Excel sale côté interface -> Alex / implémentation.

### Q98 - Format des messages d'erreur Excel sale
- Question : quel format utiliser pour les refus d'import Excel côté interface ?
- Capture : décision pour des messages structurés avec détails techniques dépliables. Chaque message métier doit avoir un titre clair, une cause, un emplacement et une action à faire. Exemple : `Colonnes masquées détectées`, onglet `Dossiers`, colonnes `AG`, `AH`, action `affichez ou supprimez ces colonnes puis réimportez`. Les détails bruts restent disponibles dans une zone technique dépliable pour debug.
- Drapeaux : définir les causes de refus Excel à traiter dès la V1 -> Alex / implémentation.

### Q99 - Causes de refus Excel V1
- Question : faut-il retenir une liste de refus strict limité, strict élargi ou maximal pour les fichiers Excel ambigus ?
- Capture : décision pour un refus strict élargi en V1. Les causes bloquantes sont : cellules fusionnées, en-têtes multi-lignes, colonnes masquées, formules, absence ou ambiguïté `id_dossier`, lignes masquées, onglets masqués, colonnes avec données sans en-tête, doublons `id_dossier`, collisions de noms CSV après nettoyage.
- Drapeaux : décider le statut des doublons d'en-têtes source dans le diagnostic et l'interface -> Alex / implémentation.

### Q100 - Doublons d'en-têtes source
- Question : les doublons d'en-têtes source doivent-ils bloquer l'import, être signalés en alerte non bloquante, ou être ignorés ?
- Capture : décision pour les signaler en alerte non bloquante. L'utilisateur voit le risque, mais peut continuer grâce à la provenance complète `onglet + lettre colonne + nom original`, qui permet de distinguer les colonnes dans le mapping et le CSV.
- Drapeaux : définir les transitions autorisées entre statuts ou passer à une spec d'implémentation -> Alex / implémentation.

### Q101 - Suite du cadrage orchestration
- Question : faut-il continuer à cuisiner les transitions de statut, passer à une spec d'implémentation orchestration, ou passer directement au code ?
- Capture : décision pour continuer à cuisiner les transitions de statut, puis passer ensuite à une spec d'implémentation orchestration. L'objectif est de fermer le cadrage métier sans détailler excessivement l'implémentation dans la discussion.
- Drapeaux : cadrer les transitions de statut restantes -> Alex / implémentation.

### Q102 - Statut annulé
- Question : le statut `annulé` doit-il s'appliquer seulement au lot/job, au lot/job et à l'étape active, ou être remplacé par `échouée` avec motif d'annulation ?
- Capture : décision pour ajouter `annulé` au niveau lot/job et au niveau de l'étape active. Lors d'une annulation coopérative, le lot/job passe `annulé`, l'étape en cours passe aussi `annulée`, et les étapes suivantes restent `non démarrée` ou `ignorée` selon le contexte.
- Drapeaux : cadrer le comportement quand une étape se termine avec alertes non bloquantes -> Alex / implémentation.

### Q103 - Transition avec alertes non bloquantes
- Question : quand une étape produit des alertes non bloquantes, faut-il la mettre en `action requise`, `terminée avec alertes`, ou `terminée` avec problèmes séparés ?
- Capture : décision pour le statut `terminée avec alertes`, avec continuation automatique jusqu'au prochain point de validation humaine. Les alertes restent visibles dans les problèmes structurés par étape, mais ne bloquent pas le pipeline tant qu'elles ne sont pas de sévérité `bloquant`.
- Drapeaux : cadrer le statut des étapes en attente de validation humaine -> Alex / implémentation.

### Q104 - Validation humaine attendue
- Question : quel statut utiliser pour les étapes en attente de validation humaine ?
- Capture : décision pour le statut `action requise` quand une validation humaine est attendue, notamment pour `mapping`, tri, aperçu CSV et package final. Ce statut indique clairement que l'application attend une décision utilisateur, sans confondre cette attente avec un blocage technique ou métier.
- Drapeaux : distinguer les statuts `bloquée` et `échouée` -> Alex / implémentation.

### Q105 - Statuts bloquée et échouée
- Question : comment distinguer `bloquée` et `échouée` ?
- Capture : décision confirmée. `bloquée` signifie qu'une correction utilisateur est attendue, par exemple un Excel à corriger ou une validation métier à reprendre. `échouée` signifie une erreur technique ou inattendue, par exemple exception serveur, erreur d'écriture, bug de conversion ou incohérence non prévue.
- Drapeaux : produire une spec d'implémentation orchestration -> implémentation.

### Q106 - Publication de la spec orchestration
- Question : le dépôt ne documente pas de tracker ni de labels `ready-for-agent`; faut-il publier la spec d'orchestration en Markdown local ?
- Capture : décision pour une spec Markdown locale dans `docs/specs/`, validée par Alex.
- Drapeaux : Aucun.

## Matrice connu-inconnu consolidée

### Connus connus
- Les scripts actifs sont dans `scripts-2025/`.
- Le master orchestre `0-si-cellule-vide-na.py` à `12-verify_data_integrity.py`.
- Q72 confirme que les logiques métier 2025 ont été couvertes : Excel, mapping, fusion par `id_dossier`, renommage InDesign, `imageid`, `@pathimg`, images, CSV UTF-16, logs, rapport et intégrité.
- Q73 corrige la règle des valeurs absentes : `#N/A` partout est obsolète ; le CSV final 2026 doit conserver les cellules vides comme le CSV 2025 de référence.
- Q76 corrige le point dates : si elles sont présentes, les dates sont traitées au format `dd/mm/yyyy`, avec erreurs signalées et cellule vide dans le CSV final.
- Q74 réduit le risque gabarit InDesign : le CSV 2025 a été réimporté sans problème ; la contrainte prioritaire est donc de conserver strictement son format de sortie.
- Q78 fixe la posture Excel sale : import refusé si la structure est ambiguë ou non fiable, avec explication claire.
- Q79 fixe le corpus de validation : Excels réels locaux pour non-régression structurelle, Excels synthétiques générables pour tests reproductibles sans données métier.
- Q80 ouvre un cadrage manquant : l'orchestration 2026 doit être décidée explicitement, car elle conditionne l'UX, les tâches de fond, les reprises et les preuves de traitement.
- Q82 fixe le modèle V1 : pipeline typé avec états persistés, chaque étape exposant statut, inputs/outputs, warnings, artefacts et logs.
- Q83 fixe la persistance V1 : SQLite local pour l'état structuré, dossiers d'artefacts par lot pour les fichiers lourds.
- Q84 fixe les étapes visibles V1 : `upload_excel`, `diagnostic_excel`, `mapping`, `fusion_multi_onglets`, `normalisation_contenu`, `previsualisation_csv`, `upload_images`, `traitement_images`, `package_final`.
- Q85/Q102 fixent les statuts métier côté UI en français, avec identifiants internes stables sans accents, dont `annulé` pour lot/job et étape active.
- Q86 fixe le déclenchement V1 : pipeline semi-automatique, avance automatique sur les étapes sûres et validations humaines pour mapping, tri, aperçu CSV et package final.
- Q87 fixe le mécanisme de tâche de fond V1 : worker local intégré avec file SQLite.
- Q88 fixe la reprise V1 : relance depuis l'étape échouée avec invalidation automatique des étapes suivantes.
- Q89 fixe l'annulation V1 : annulation coopérative entre sous-étapes, puis lot marqué `annulé`.
- Q90 fixe les seuils V1 par défaut, configurables par environnement : Excel 50 Mo, zip 1 Go, 1500 images, 50 Mo/image, décompressé 3 Go.
- Q91 fixe le schéma SQLite opérationnel : `lots`, `etapes`, `jobs`, `artefacts`, `evenements`, `problemes`.
- Q92 fixe la conservation V1 : 7 jours par défaut configurable, avec suppression manuelle immédiate du lot.
- Q93 fixe la suppression manuelle : purge métier immédiate avec conservation d'une trace technique anonymisée.
- Q94 fixe le suivi disque visible : indicateur global et par lot, avec alerte si un seuil disque est approché.
- Q95 fixe la séparation V1 : problèmes métier structurés par étape dans l'interface, logs techniques séparés pour debug.
- Q96 fixe les sévérités métier : `bloquant`, `alerte`, `information`.
- Q97 fixe la priorité de cadrage suivante : messages d'erreur Excel sale côté interface.
- Q98 fixe le format des erreurs Excel sale : message structuré actionnable avec détails techniques dépliables.
- Q99 fixe les causes de refus Excel V1 en mode strict élargi : cellules fusionnées, en-têtes multi-lignes, colonnes/lignes/onglets masqués, formules, `id_dossier` absent/ambigu/dupliqué, colonnes avec données sans en-tête, collisions de noms CSV après nettoyage.
- Q100 fixe les doublons d'en-têtes source : alerte non bloquante, car la provenance complète permet de les distinguer.
- Q101 fixe la suite : terminer le cadrage des transitions de statut, puis produire une spec d'implémentation orchestration.
- Q102 fixe le statut `annulé` : il s'applique au lot/job et à l'étape active.
- Q103 fixe les alertes non bloquantes : étape `terminée avec alertes`, puis continuation jusqu'au prochain point de validation humaine.
- Q104 fixe les validations humaines : statut `action requise` pour mapping, tri, aperçu CSV et package final.
- Q105 fixe la distinction : `bloquée` = correction utilisateur attendue ; `échouée` = erreur technique ou inattendue.
- Q106 fixe la publication : spec d'implémentation orchestration en Markdown local dans `docs/specs/`.

### Connus inconnus
- `[^]` Le vrai fichier Excel 2026 n'existe pas encore : structure, noms d'onglets, emplacement exact de `id_dossier`.
- `[~]` Les profils de mapping doivent encore être formalisés techniquement.
- `[~]` Le package final exact reste à figer.
- `[~]` HEIC/Pillow doit être testé sur Mac Alex puis VPS.
- `[~]` Authentification, rétention des logs et contraintes VPS restent à préciser plus tard.
- `[~]` Q75/Q77 cadrent le risque gros volumes : traitements lourds en tâche de fond, progression visible et seuils configurables. Reste à définir les transitions de statut.
- `[~]` Q78 cadre l'import Excel sale : refus strict élargi, avec doublons d'en-têtes source en alerte non bloquante.
- `[~]` Le cadrage orchestration Q80-Q106 est prêt à transformer en spec d'implémentation locale.

### Inconnus connus
- `[^]` Le multi-onglets 2026 est une extension : les scripts 2025 ne faisaient pas une vraie fusion multi-onglets.
- `[~]` Les dates étaient neutralisées dans le script actif 2025 parce que la structure active ne les utilisait plus ; elles redeviennent une règle conditionnelle 2026 si le fichier source en contient.
- `[~]` Les sorties vides doivent être testées comme non-régression InDesign, non parce que la règle est ouverte, mais parce que la fidélité au CSV 2025 doit être prouvée.
- `[~]` Les vrais fichiers `Sircom1.xlsx` et `Sircom2.xlsx` apportent des formes historiques utiles, mais ne remplacent pas les fixtures synthétiques versionnables.

### Inconnus inconnus
- `[~]` Excel réel avec cellules fusionnées, en-têtes sur plusieurs lignes, colonnes masquées ou formules : posture décidée en Q78, refus d'import avec message clair.
- `[~]` Gros volumes réels supérieurs aux seuils V1 : zip lourd, beaucoup d'images, images très grandes, traitement long ou interruption serveur. La tâche de fond réduit le risque de timeout, mais ne remplace pas les limites de volume et le nettoyage temporaire.
- `[.]` Gabarit InDesign 2026 plus strict que prévu : risque résiduel faible si le format CSV 2025 est strictement conservé, à couvrir par test de non-régression.

## Drapeaux ouverts

- Structure exacte du fichier Excel 2026 inconnue -> Sircom.
- Règles définitives de mapping et de validation à cadrer -> Alex / Sircom.
- Format de stockage et portée des profils de mapping à définir -> Alex / implémentation.
- Confirmer dans le fichier source réel que l'identifiant dossier est présent et stable dans tous les onglets utiles -> Sircom.
- Format du dictionnaire de correspondance à dériver du mapping 2025, avec ajout de l'onglet source pour 2026 -> implémentation.
- Confirmer la règle images avec le fichier 2026 réel et la convention de livraison du lot -> Sircom.
- Format exact du rapport téléchargeable à définir -> implémentation.
- Liste exacte des fichiers du package zip à figer dans la spécification -> implémentation.
- Durée de rétention et contenu exact des logs techniques à définir, avec masquage des données sensibles -> implémentation.
- Contraintes d'authentification, stockage et exploitation du VPS interne à préciser plus tard -> Sircom / DSI.
- Audit RGAA/DSFR à prévoir avant publication ; claims de conformité interdits sans preuve dédiée -> implémentation.
- Mode d'intégration de l'authentification VPS à préciser plus tard -> Alex / VPS.
- Définir précisément `export testable` dans les critères techniques -> implémentation.
- Prévoir un test de non-régression sur les caractéristiques du CSV 2025 de référence -> implémentation.
- Produire la spec d'implémentation orchestration locale -> implémentation.
- Tester la détection et la conversion des dates sur le jeu Excel synthétique puis sur le vrai fichier 2026 -> implémentation.
- Compléter les fixtures synthétiques avec des scénarios de mapping, CSV, images et package final -> implémentation.
- Transformer la parité 2025 en backlog MVP découpé -> implémentation.
- Cible long terme : gestion multi-lots, auth prod, tableau de bord, historique -> post-MVP.
- Vérifier les formats réellement supportés par Pillow dans l'environnement cible et documenter les échecs de conversion -> implémentation.
- Vérifier la disponibilité HEIC et les dépendances Pillow sur Mac Alex puis sur VPS interne -> implémentation.
