# TODO

État au 21 juillet 2026.

## Terminé

- [x] Ajouter un diagnostic automatique Excel 2026 : structure détectée, onglets,
  colonnes, clé logique `id_dossier`, alertes et blocages.
- [x] Créer un générateur de fichiers Excel synthétiques multi-onglets.
  - [x] Inclure des onglets multiples avec `id_dossier` comme clé commune.
  - [x] Varier l'ordre des colonnes et la position de `id_dossier`.
  - [x] Prévoir des colonnes région/département présentes.
  - [x] Couvrir cellules vides, colonnes entièrement vides, lignes sans
    `id_dossier` et formats sensibles.
  - [x] Couvrir les refus V1 : ID manquant, ID dupliqué, ID ambigu, cellules
    fusionnées, colonnes masquées, formules et en-têtes multi-lignes.
- [x] Ajouter les tests unitaires ciblés du diagnostic Excel.
- [x] Utiliser les Excels réels `Sircom1.xlsx` et `Sircom2.xlsx` comme
  non-régression structurelle locale quand ils sont présents.
- [x] Formaliser la spec fonctionnelle globale Sircom 2026 dans `docs/specs/`.
- [x] Formaliser la spec locale d'orchestration Sircom 2026 dans `docs/specs/`.
- [x] Produire le design d'architecture reliant contrat fonctionnel,
  orchestration, modules, routes, SQLite, worker et artefacts.
- [x] Mettre à jour `README.md` sans emojis avec l'état 2025/2026 du dépôt.

## Priorité 0 - Verrouiller avant codage lourd

- [x] Découper les specs fonctionnelle, orchestration et architecture en tickets
  unitaires, avec preuve observable pour chaque ticket.
- [x] Transformer les quatre risques bloquants de la spec d'architecture en
  critères d'acceptation explicites :
  - [x] cohérence SQLite/disque et `ArtifactStore` atomique ;
  - [x] idempotence worker, `run_id`, leases et double soumission ;
  - [x] frontière `AccessPolicy` / `ActorContext` prête pour le futur VPS ;
  - [x] oracle CSV exécutable avant writer final.
- [x] Relire chaque ticket unitaire avec une passe connu-inconnu et avocat du
  diable.
- [x] Trancher la stack frontend V1 : templates FastAPI/Jinja + DSFR et
  JavaScript minimal par défaut, sauf décision explicite contraire.
- [x] Définir précisément `export testable` comme checklist bloquante du package
  final.
- [x] Définir le format du rapport téléchargeable et la liste exacte des fichiers
  du package final au-delà du minimum décidé.
- [x] Trancher la politique V1 pour les zips images avec sous-dossiers : refus,
  avertissement ou extraction encadrée.
- [x] Encadrer la décision HEIC dans le ticket 19 : support testé, refus clair
  ou dépendance optionnelle documentée.
- [x] Appliquer le patch P0 de lancement ticket 01 : defaults V1
  `SIRCOM_MAX_ACTIVE_JOBS=1`, `SIRCOM_DISK_FREE_MIN_MB=5120` et contrat
  `/health/ready` testable.
- [x] Fermer la passe de décisions avant tickets 03 et aval : schéma run-scopé,
  machine d'états, store d'artefacts et réconciliation, worker lease/fencing,
  DAG/fingerprints, bindings images, mapping profils/rôles, purge/disque et
  sémantique CSV/package.
- [x] Formaliser le contrat UI DSFR V1 : shell, écrans métier, composants,
  états, messages, formulaires, responsive et vérifications minimales.
- [x] Ajouter les garde-fous d'implémentation agent : prompt verrouillé ticket
  01 et template de review post-ticket.
- [ ] Clarifier avec le Sircom le couplage gabarit InDesign 2026 : nouveaux noms
  `id_dossier`/mapping ou réemploi des champs 2025.

## Prochain incrément - Socle web local

- [x] Créer le squelette FastAPI minimal sans routes stub de succès.
- [x] Ajouter `pyproject.toml` pour FastAPI, tests et runtime local.
- [x] Ajouter `.sircom2026-data/` au `.gitignore`.
- [x] Implémenter la configuration `sircom2026.config` :
  - [x] `SIRCOM_DATA_DIR` ;
  - [x] `SIRCOM_SQLITE_PATH` ;
  - [x] limites Excel, zip, images et disque ;
  - [x] `SIRCOM_INDESIGN_IMAGE_ROOT` ;
  - [x] bind host, port et worker activable.
- [x] Implémenter `GET /health`, `GET /health/ready` et OpenAPI.
- [x] Tester `/health/ready` avec répertoire de données temporaire, SQLite et
  seuil d'espace disque.
- [x] Implémenter le parcours lots V1 : création, consultation, suppression
  logique, liste active et timeline UI DSFR.

## Orchestration et stockage

- [x] Implémenter le schéma SQLite minimal :
  - [x] `lots` ;
  - [x] `etapes` ;
  - [x] `jobs` ;
  - [x] `artefacts` ;
  - [x] `evenements` ;
  - [x] `problemes`.
- [x] Ajouter les contraintes d'unicité et clés étrangères nécessaires pour
  empêcher deux jobs actifs incompatibles.
- [x] Implémenter les repositories lots, étapes, jobs, artefacts, événements et
  problèmes.
- [x] Implémenter le `ArtifactStore` :
  - [x] écritures dans `tmp/` ;
  - [x] promotion atomique ;
  - [x] empreinte SHA-256 ;
  - [x] états `pending`, `committed`, `obsolete` ;
  - [x] réconciliation au démarrage après échec simulé.
- [x] Implémenter la couche d'état métier affichable :
  - [x] transitions `termine`, `termine_avec_alertes`, `action_requise`,
    `bloque`, `echoue` et `annule` ;
  - [x] problèmes structurés avec code, titre, cause, emplacement, action et
    détails techniques ;
  - [x] événements techniques persistés séparément des problèmes métier ;
  - [x] rendu DSFR minimal des problèmes par niveau et des événements récents.
- [x] Implémenter le worker local minimal :
  - [x] acquisition de lease ;
  - [x] `run_id` par étape ;
  - [x] progression persistée ;
  - [x] annulation coopérative ;
  - [x] retry avec invalidation aval.
- [x] Tester les transitions `action_requise`, `bloque`, `termine`,
  `termine_avec_alertes`, `echoue` et `annule`.
- [ ] Tester la transition `ignore` quand un ticket métier l'introduira ;
  `non_demarre`, `pret`, `en_cours` et `invalide` sont couverts par les tickets
  07 et 08.

## Import Excel et mapping

- [x] Ajouter la route d'upload Excel FastAPI avec stockage artefact source et
  planification du job `diagnostic_excel`, sans exécuter le diagnostic dans la
  requête HTTP.
- [x] Refuser les uploads Excel trop gros, extension invalide ou archive
  illisible avec erreurs structurées.
- [x] Brancher `sircom2026.excel_diagnostic` au job `diagnostic_excel` sans
  déplacer la logique métier dans la route.
- [x] Persister le diagnostic Excel et les problèmes structurés sans exposer de
  valeurs métier.
- [x] Vérifier que les refus V1 produisent un message avec titre, cause,
  emplacement, action et détails techniques dépliables.
- [x] Implémenter le mapping par défaut avec toutes les colonnes de tous les
  onglets utiles.
- [x] Conserver la provenance complète du mapping : onglet source, lettre
  colonne, nom original, nom CSV final et statut exporté ou supprimé.
- [x] Valider humainement le mapping avant fusion.
- [x] Définir le format des profils de mapping :
  - [x] empreinte de structure ;
  - [x] compatibilité partielle ;
  - [x] brouillon seulement, jamais application silencieuse ;
  - [x] validation humaine obligatoire.
- [x] Ajouter des tests de collisions de noms CSV après nettoyage.

## Fusion, normalisation et CSV

- [ ] Implémenter la fusion à plat par clé logique `id_dossier`.
- [ ] Garantir une seule colonne `id_dossier` exportée.
- [ ] Placer `imageid` et `@pathimg` juste après `id_dossier`.
- [ ] Supprimer et compter les lignes sans `id_dossier`.
- [ ] Supprimer et compter les colonnes entièrement vides, même sélectionnées.
- [ ] Normaliser les cellules :
  - [ ] retours ligne convertis en `<br>` ;
  - [ ] espaces début/fin supprimés ;
  - [ ] espaces multiples réduits ;
  - [ ] champs sensibles préservés en texte.
- [ ] Convertir les dates valides en `dd/mm/yyyy` pour les colonnes détectées ou
  confirmées comme dates.
- [ ] Signaler les dates invalides ou absentes tout en gardant des cellules vides
  dans le CSV final.
- [ ] Implémenter la proposition de tri région puis département avec validation
  humaine.
- [ ] Conserver l'ordre Excel avec alerte non bloquante si les colonnes de tri ne
  sont pas détectées.
- [ ] Créer un vérificateur de contrat CSV avant le writer final :
  - [ ] UTF-16 avec BOM ;
  - [ ] séparateur virgule ;
  - [ ] LF ;
  - [ ] guillemets automatiques seulement si nécessaire ;
  - [ ] cellules vides conservées ;
  - [ ] comparaison structurelle avec le CSV 2025 de référence.
- [ ] Ajouter les tests de sortie CSV UTF-16 compatibles avec
  `livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`.
- [ ] Implémenter l'aperçu CSV avec en-têtes finaux, premières lignes, colonnes
  supprimées, lignes supprimées et alertes.
- [ ] Bloquer l'export si l'aperçu ne correspond plus aux empreintes courantes.

## Images

- [ ] Ajouter les fixtures image/zip pour tester matching, absences, ambiguïtés
  et images non référencées.
- [ ] Étendre les fichiers synthétiques avec colonnes région/département
  absentes ou mal nommées.
- [ ] Ajouter des noms d'onglets longs et des cas de collisions de mapping
  multi-onglets.
- [ ] Implémenter l'upload d'un seul zip images par lot.
- [ ] Sécuriser l'inspection zip :
  - [ ] refus `zip slip` ;
  - [ ] bornes taille zip, taille décompressée, nombre d'images et taille image ;
  - [ ] normalisation des noms ;
  - [ ] fichiers cachés ignorés ou signalés selon politique ;
  - [ ] logs sans valeurs métier sensibles.
- [ ] Implémenter le matching images :
  - [ ] correspondance par nom original si disponible ;
  - [ ] fallback par `id_dossier` normalisé ;
  - [ ] tolérances casse, espaces, extension, tirets et underscores ;
  - [ ] ambiguïtés en résolution manuelle ;
  - [ ] images absentes non bloquantes ;
  - [ ] images non référencées ignorées mais listées.
- [ ] Produire les images finales en JPG :
  - [ ] nom `dossier-{id-normalise}.jpg` ;
  - [ ] largeur maximale 350 px ;
  - [ ] qualité JPEG 100 ;
  - [ ] DPI 300 ;
  - [ ] fond blanc pour transparence ;
  - [ ] orientation EXIF appliquée.
- [ ] Tester l'écart Mac/VPS pour Pillow, profils ICC, EXIF, transparence et
  support HEIC décidé.
- [ ] Exécuter le spike HEIC du ticket 19 et reporter la décision dans les
  formats images acceptés.

## Package, rapports et exploitation

- [ ] Générer le rapport métier avec mapping complet, intégrité, suppressions,
  absences, alertes images et décisions utilisateur.
- [ ] Séparer strictement rapport métier et logs techniques.
- [ ] Générer le package final avec au minimum :
  - [ ] CSV final compatible InDesign ;
  - [ ] `export-jpg-resize/` ;
  - [ ] rapport métier ;
  - [ ] mapping utilisé ;
  - [ ] manifeste cohérent.
- [ ] Vérifier que `@pathimg` vise
  `/Users/victoria/Documents/export-jpg-resize` par défaut, sauf configuration
  explicite.
- [ ] Autoriser le téléchargement uniquement par `artifact_id`, sans exposer les
  chemins disque internes.
- [ ] Bloquer le package si des problèmes bloquants restent ouverts.
- [ ] Implémenter suppression manuelle, purge, rétention configurable et trace
  technique anonymisée.
- [ ] Ajouter indicateurs disque : usage total, espace libre, lots les plus
  lourds, date d'expiration et alerte seuil.

## Documentation et recette

- [x] Documenter le démarrage local de l'application web quand le squelette
  FastAPI existe.
- [ ] Ajouter un guide court de correction des Excels refusés.
- [ ] Ajouter une recette de bout en bout avec fixtures synthétiques.
- [ ] Documenter les variables d'environnement V1.
- [ ] Maintenir `README.md`, `CHANGELOG.md` et `TODO.md` après chaque incrément
  significatif.
