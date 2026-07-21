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

- [ ] Découper les specs fonctionnelle, orchestration et architecture en tickets
  unitaires, avec preuve observable pour chaque ticket.
- [ ] Transformer les quatre risques bloquants de la spec d'architecture en
  critères d'acceptation explicites :
  - [ ] cohérence SQLite/disque et `ArtifactStore` atomique ;
  - [ ] idempotence worker, `run_id`, leases et double soumission ;
  - [ ] frontière `AccessPolicy` / `ActorContext` prête pour le futur VPS ;
  - [ ] oracle CSV exécutable avant writer final.
- [ ] Trancher la stack frontend V1 : templates FastAPI/Jinja + DSFR et
  JavaScript minimal par défaut, sauf décision explicite contraire.
- [ ] Définir précisément `export testable` comme checklist bloquante du package
  final.
- [ ] Définir le format du rapport téléchargeable et la liste exacte des fichiers
  du package final au-delà du minimum décidé.
- [ ] Trancher la politique V1 pour les zips images avec sous-dossiers : refus,
  avertissement ou extraction encadrée.
- [ ] Décider la stratégie HEIC : support testé, refus clair ou dépendance
  optionnelle documentée.

## Prochain incrément - Socle web local

- [ ] Créer le squelette FastAPI minimal sans routes stub de succès.
- [ ] Ajouter `pyproject.toml` ou fichier de dépendances équivalent pour
  FastAPI, tests et runtime local.
- [ ] Ajouter `.sircom2026-data/` au `.gitignore`.
- [ ] Implémenter la configuration `sircom2026.config` :
  - [ ] `SIRCOM_DATA_DIR` ;
  - [ ] `SIRCOM_SQLITE_PATH` ;
  - [ ] limites Excel, zip, images et disque ;
  - [ ] `SIRCOM_INDESIGN_IMAGE_ROOT` ;
  - [ ] bind host, port et worker activable.
- [ ] Implémenter `GET /health`, `GET /health/ready` et OpenAPI.
- [ ] Tester `/health/ready` avec répertoire de données temporaire, SQLite et
  seuil d'espace disque.

## Orchestration et stockage

- [ ] Implémenter le schéma SQLite minimal :
  - [ ] `lots` ;
  - [ ] `etapes` ;
  - [ ] `jobs` ;
  - [ ] `artefacts` ;
  - [ ] `evenements` ;
  - [ ] `problemes`.
- [ ] Ajouter les contraintes d'unicité et clés étrangères nécessaires pour
  empêcher deux jobs actifs incompatibles.
- [ ] Implémenter les repositories lots, étapes, jobs, artefacts, événements et
  problèmes.
- [ ] Implémenter le `ArtifactStore` :
  - [ ] écritures dans `tmp/` ;
  - [ ] promotion atomique ;
  - [ ] empreinte SHA-256 ;
  - [ ] états `pending`, `committed`, `obsolete` ;
  - [ ] réconciliation au démarrage après échec simulé.
- [ ] Implémenter le worker local minimal :
  - [ ] acquisition de lease ;
  - [ ] `run_id` par étape ;
  - [ ] progression persistée ;
  - [ ] annulation coopérative ;
  - [ ] retry avec invalidation aval.
- [ ] Tester les transitions `non_demarre`, `pret`, `en_cours`,
  `action_requise`, `bloque`, `termine`, `termine_avec_alertes`, `echoue`,
  `ignore` et `annule`.

## Import Excel et mapping

- [ ] Brancher `sircom2026.excel_diagnostic` à la route d'upload Excel FastAPI
  sans déplacer la logique métier dans la route.
- [ ] Refuser les uploads Excel trop gros, extension invalide ou type non
  exploitable.
- [ ] Persister le diagnostic Excel et les problèmes structurés sans exposer de
  valeurs métier.
- [ ] Vérifier que les refus V1 produisent un message avec titre, cause,
  emplacement, action et détails techniques dépliables.
- [ ] Implémenter le mapping par défaut avec toutes les colonnes de tous les
  onglets utiles.
- [ ] Conserver la provenance complète du mapping : onglet source, lettre
  colonne, nom original, nom CSV final et statut exporté ou supprimé.
- [ ] Valider humainement le mapping avant fusion.
- [ ] Définir le format des profils de mapping :
  - [ ] empreinte de structure ;
  - [ ] compatibilité partielle ;
  - [ ] brouillon seulement, jamais application silencieuse ;
  - [ ] validation humaine obligatoire.
- [ ] Ajouter des tests de collisions de noms CSV après nettoyage.

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

- [ ] Documenter le démarrage local de l'application web quand le squelette
  FastAPI existe.
- [ ] Ajouter un guide court de correction des Excels refusés.
- [ ] Ajouter une recette de bout en bout avec fixtures synthétiques.
- [ ] Documenter les variables d'environnement V1.
- [ ] Maintenir `README.md`, `CHANGELOG.md` et `TODO.md` après chaque incrément
  significatif.
