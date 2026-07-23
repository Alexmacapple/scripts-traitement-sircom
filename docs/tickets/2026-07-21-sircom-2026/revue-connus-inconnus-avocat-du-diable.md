# Revue connu-inconnu et avocat du diable des tickets Sircom 2026

Date : 2026-07-21

Cible relue : les 23 tickets unitaires du dossier
`docs/tickets/2026-07-21-sircom-2026/`.

Sources comparées :

- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `AGENTS.md`

## Verdict

Verdict : livrer avec modifications appliquées, sans tension LLM bloquante
résiduelle.

Les 23 tickets restent unitaires et couvrent les specs sans trou majeur détecté.
La frontier initiale reste le ticket 01 uniquement. Les corrections ajoutées
renforcent les critères d'acceptation, sans créer de nouveau ticket.

Note post-revues GLM/SOL/Codex : ce verdict est conservé comme revue de découpage,
mais il n'est plus le verdict d'exécution courant. Le verdict courant est :
ticket 01 exécutable après patch P0 ; ticket 02 ouvrable après 01 ; ticket 03 et
tickets métier/worker/images/purge à durcir avant ouverture selon
`docs/audits/2026-07-21-synthese-verification-globale-sircom-2026.md`.

## Steel-man global

Le découpage est raisonnable parce qu'il suit le flux métier réel : socle,
accès, persistance, lots, artefacts, états, worker, invalidation, Excel, mapping,
CSV, images, rapports, package et purge. Chaque ticket a une preuve observable,
ce qui limite le risque de grands chantiers impossibles à valider.

Le choix de fichiers Markdown unitaires est adapté au dépôt actuel, car aucun
tracker local formalisé n'existe encore. Les dépendances explicites rendent le
graphe exécutable par sessions agent courtes.

## Quadrants globaux

### Connus connus

- `[^]` Les règles CSV InDesign, Excel sale, images, worker et purge sont
  couvertes par des tickets dédiés.
- `[^]` Les quatre risques bloquants des specs ont des tickets : cohérence
  artefacts, idempotence worker, accès local futur-compatible et oracle CSV.
- `[~]` Le ticket 01 est volontairement la seule frontier initiale.

### Connus inconnus

- `[~]` Le support HEIC réel est une décision bornée dans le ticket 19.
- `[~]` Le format du rapport métier est fixé pour la V1 dans le ticket 21.
- `[~]` Les contraintes VPS réelles restent hors V1, mais l'interface
  `AccessPolicy` évite une impasse.

### Inconnus connus

- `[^]` Un agent peut vouloir créer toute l'arborescence cible d'un coup.
  Mitigation : les règles globales interdisent les modules vides.
- `[^]` La référence 2025 peut être mal comprise comme une liste de colonnes
  fixe. Mitigation : le ticket 16 le limite à un oracle de format.
- `[~]` Les zips réels peuvent contenir Unicode, sous-dossiers ou doublons après
  normalisation. Mitigation : ticket 18 renforcé.

### Inconnus inconnus

- `[^]` Un Excel 2026 réel peut combiner plusieurs anomalies absentes des
  fichiers 2024/2025.
- `[^]` InDesign peut révéler une contrainte implicite non capturée par le seul
  CSV 2025 de référence.
- `[~]` Le passage VPS peut changer les contraintes disque, image ou sécurité.

## Avocat du diable global

1. Le ticket 01 pouvait devenir un socle trop large.
   Sévérité : moyenne. Statut : corrigé.
   Recommandation appliquée : choix Jinja/DSFR statique, endpoint limites et
   tests de configuration explicités.

2. La cohérence SQLite/disque pouvait rester trop implicite.
   Sévérité : haute. Statut : corrigé.
   Recommandation appliquée : ticket 05 renforcé avec états non téléchargeables
   et contrôle de cohérence fichier/base.

3. Le worker pouvait ignorer les cas restart, double soumission ou traitement en
   requête HTTP.
   Sévérité : haute. Statut : corrigé.
   Recommandation appliquée : tickets 07 et 08 renforcés sur `run_id`, leases,
   snapshots et absence de `BackgroundTasks` critiques.

4. Le CSV 2025 pouvait être surinterprété comme liste normative de colonnes.
   Sévérité : haute. Statut : corrigé.
   Recommandation appliquée : ticket 16 précise que la référence 2025 est un
   oracle de format.

5. Les uploads étaient la surface d'attaque la plus concrète.
   Sévérité : haute. Statut : corrigé.
   Recommandation appliquée : tickets 09 et 18 renforcés sur archive corrompue,
   nom interne, signature zip, Unicode et nettoyage temporaire.

6. Les images Mac/VPS et HEIC pouvaient laisser une dépendance implicite.
   Sévérité : moyenne. Statut : borné dans le ticket 19.
   Recommandation appliquée : le ticket 19 demande une décision explicite et
   alimente les formats acceptés par le ticket 20.

7. La purge pouvait courir en parallèle d'une écriture d'artefact.
   Sévérité : haute. Statut : corrigé.
   Recommandation appliquée : ticket 23 impose annulation coopérative, purge non
   concurrente et idempotence.

## Revue par ticket

### 01 - Socle FastAPI, configuration, santé et UI shell DSFR

- Connu-inconnu : ancrage sur FastAPI/config/santé ; brouillard sur choix
  frontend ; déni possible autour d'un socle trop large ; abîme sur
  configuration invalide selon environnement.
- Avocat du diable : risque de créer une UI ou une arborescence prématurée.
- Résultat : renforcé avec Jinja/DSFR statique, `/api/config/limits` et tests de
  configuration. Prêt.

### 02 - Politique d'accès locale et erreurs API structurées

- Connu-inconnu : ancrage sur V1 locale sans auth ; brouillard sur VPS futur ;
  déni possible autour du mono-utilisateur ; abîme sur accès croisé aux lots.
- Avocat du diable : sans actions nommées, l'accès local deviendrait du code mort
  impossible à remplacer.
- Résultat : renforcé avec actions d'accès nommées et non-divulgation de données
  d'autres lots. Prêt.

### 03 - Schéma SQLite, migrations et repositories de base

- Connu-inconnu : ancrage sur les six tables ; brouillard sur contraintes
  exactes ; déni possible autour de migrations "simples" ; abîme sur statut
  invalide qui
  contamine le pipeline.
- Avocat du diable : une base qui se crée sans version ni contraintes devient
  fragile dès le worker.
- Résultat : renforcé avec migrations idempotentes et validation/contrainte des
  statuts critiques. Prêt.

### 04 - Lots, consultation, suppression logique et timeline UI

- Connu-inconnu : ancrage sur création/consultation/suppression logique ;
  brouillard sur volume de lots ; déni possible autour de listes non bornées ;
  abîme sur lots supprimés visibles par erreur.
- Avocat du diable : une liste sans pagination ni filtrage des supprimés peut
  fausser l'UI et les tests.
- Résultat : renforcé avec pagination simple, exclusion des supprimés et libellés
  français de timeline. Prêt.

### 05 - Store d'artefacts atomique et téléchargements

- Connu-inconnu : ancrage sur `ArtifactStore` et `artifact_id` ; brouillard sur
  réconciliation ; déni possible autour de fichiers "juste sur disque" ; abîme
  sur divergence SQLite/fichier après crash.
- Avocat du diable : c'est un point de perte de cohérence majeur.
- Résultat : renforcé avec états non téléchargeables et contrôle de cohérence
  fichier/base. Prêt.

### 06 - Statuts métier, événements, problèmes et logs

- Connu-inconnu : ancrage sur statuts et sévérités ; brouillard sur transitions
  exhaustives ; déni possible entre `bloquant` et `bloque` ; abîme sur étape
  marquée terminée malgré alertes.
- Avocat du diable : mauvais statut égale mauvaise action utilisateur.
- Résultat : renforcé avec `action_requise`, `annule` et interdiction de masquer
  les alertes en `termine`. Prêt.

### 07 - Worker local, file SQLite, idempotence et annulation

- Connu-inconnu : ancrage sur worker local et leases ; brouillard sur restart ;
  déni possible autour de double clics ; abîme sur traitement lourd lancé dans la
  requête HTTP.
- Avocat du diable : c'est le ticket le plus exposé aux courses et aux états
  partiels.
- Résultat : renforcé avec absence de `BackgroundTasks` critiques et comportement
  après redémarrage. Prêt après 05 et 06.

### 08 - Retry et invalidation aval par fingerprints

- Connu-inconnu : ancrage sur relance et invalidation ; brouillard sur graphe
  exact ; déni possible autour d'artefacts périmés ; abîme sur validation humaine
  relue après modification d'input.
- Avocat du diable : sans graphe central, les endpoints vont diverger.
- Résultat : renforcé avec graphe centralisé et snapshots de validation. Prêt
  après 07.

### 09 - Upload Excel sécurisé

- Connu-inconnu : ancrage sur upload Excel ; brouillard sur archives corrompues ;
  déni possible autour du nom original ; abîme sur diagnostic lancé en requête
  HTTP.
- Avocat du diable : l'upload est une surface d'attaque et un déclencheur
  d'invalidation.
- Résultat : renforcé avec archive illisible, nom interne et diagnostic hors
  requête. Prêt après 05 et 08.

### 10 - Diagnostic Excel persisté

- Connu-inconnu : ancrage sur diagnostic existant ; brouillard sur combinaisons
  d'anomalies ; déni possible autour de l'Excel refusé ; abîme sur diagnostic qui
  s'arrête au premier problème.
- Avocat du diable : refuser sans aider à corriger crée un contournement manuel.
- Résultat : renforcé avec onglet vide/non vide et collecte de tous les problèmes
  détectables. Prêt après 09.

### 11 - Messages Excel sale et panneau problèmes UI

- Connu-inconnu : ancrage sur messages structurés ; brouillard sur rendu UI
  exact ; déni possible autour des détails techniques ; abîme sur fuite de valeurs
  métier dans l'aide au debug.
- Avocat du diable : un bon diagnostic technique peut être un mauvais message
  utilisateur.
- Résultat : déjà assez cadré par les critères existants. Prêt après 06 et 10.

### 12 - Mapping par défaut, profils brouillon et validation

- Connu-inconnu : ancrage sur mapping avec provenance ; brouillard sur format de
  profil ; déni possible autour de réutilisation silencieuse ; abîme sur aucune
  colonne métier sélectionnée.
- Avocat du diable : un profil compatible mais appliqué sans validation peut
  produire un CSV faux et valide.
- Résultat : renforcé avec format profil, sauvegarde depuis validation et refus
  sans colonne métier. Prêt après 11.

### 13 - Fusion multi-onglets

- Connu-inconnu : ancrage sur union des `id_dossier` ; brouillard sur cas limites
  d'absence inter-onglets ; déni possible autour du premier onglet comme source
  de vérité ; abîme sur colonne `id_dossier` secondaire exportée par erreur.
- Avocat du diable : la fusion est simple seulement si le diagnostic et le
  mapping ont réellement verrouillé les clés.
- Résultat : critères existants suffisants. Prêt après 12.

### 14 - Normalisation contenu

- Connu-inconnu : ancrage sur espaces, retours ligne, dates et texte sensible ;
  brouillard sur valeurs vides ; déni possible autour des conversions pandas ;
  abîme sur zéros initiaux perdus.
- Avocat du diable : un CSV valide peut être métier faux si les identifiants ou
  codes sont convertis.
- Résultat : renforcé avec zéros initiaux et interdiction de `nan`, `NaT`,
  `None`, `#N/A`. Prêt après 13.

### 15 - Tri région/département et validation humaine

- Connu-inconnu : ancrage sur tri proposé ; brouillard sur détection ambiguë ;
  déni possible autour d'un tri automatique trop confiant ; abîme sur ordre Excel
  conservé sans décision utilisateur.
- Avocat du diable : le tri modifie le livrable final et doit rester une
  décision humaine.
- Résultat : renforcé avec confirmation explicite du repli et refus de détection
  ambiguë automatique. Prêt après 14.

### 16 - Vérificateur de contrat CSV InDesign

- Connu-inconnu : ancrage sur UTF-16 BOM, virgule, LF ; brouillard sur
  comportement InDesign réel ; déni possible autour de la liste 2025 ; abîme sur
  normalisation texte qui masque une erreur octet.
- Avocat du diable : si le vérificateur est trop permissif, le package sera faux
  avec des tests verts.
- Résultat : renforcé avec contrôle octets et référence 2025 comme oracle de
  format seulement. Prêt après 14.

### 17 - Aperçu CSV, validation humaine et export UTF-16

- Connu-inconnu : ancrage sur aperçu et validation ; brouillard sur prérequis
  `export testable` ; déni possible autour des exports périmés ; abîme sur CSV
  téléchargeable sans artefact courant.
- Avocat du diable : l'aperçu peut rassurer l'utilisateur tout en cachant des
  suppressions.
- Résultat : renforcé avec colonnes/lignes supprimées, refus si prérequis
  manquants et artifact courant. Prêt après 15 et 16.

### 18 - Upload zip images et inspection sécurisée

- Connu-inconnu : ancrage sur zip images à la racine ; brouillard sur Unicode et
  signature ; déni possible autour des sous-dossiers réels ; abîme sur doublons
  après normalisation.
- Avocat du diable : un zip "valide" peut être dangereux ou ambigu avant même le
  matching.
- Résultat : renforcé avec signature, doublons normalisés et nettoyage temporaire
  en échec. Prêt après 05 et 08.

### 19 - Spike formats images Mac/VPS

- Connu-inconnu : ancrage sur Pillow et fixtures ; brouillard sur HEIC ; déni
  possible autour du "ça marche sur Mac" ; abîme sur VPS sans dépendance système.
- Avocat du diable : laisser HEIC implicite déplacerait le risque dans le ticket
  20.
- Résultat : renforcé avec WEBP/TIFF, dépendances système et décision alimentant
  les formats acceptés. Prêt après 18.

### 20 - Matching et traitement images

- Connu-inconnu : ancrage sur matching et conversion ; brouillard sur résolution
  manuelle ; déni possible autour d'anciens dossiers images ; abîme sur noms
  finaux incompatibles InDesign.
- Avocat du diable : le plus dangereux est un choix automatique plausible mais
  faux.
- Résultat : renforcé avec résolutions persistées, nom final 2025 et source zip
  exclusive. Prêt après 12, 18 et 19.

### 21 - Rapports métier et technique

- Connu-inconnu : ancrage sur contenu minimal ; brouillard sur format final ;
  déni possible autour des logs anonymisés ; abîme sur rapport utile au dev mais
  pas au Sircom.
- Avocat du diable : le rapport deviendra l'outil de correction et de recette.
- Résultat : renforcé avec sections fixes et tests négatifs de fuite de contenu.
  Prêt après 17 et 20.

### 22 - Package final, manifeste et téléchargements

- Connu-inconnu : ancrage sur package complet ; brouillard sur absence d'images ;
  déni possible autour de fingerprints obsolètes ; abîme sur package généré dans
  une requête HTTP.
- Avocat du diable : un package conforme techniquement peut être assemblé depuis
  des artefacts périmés.
- Résultat : renforcé avec worker, fingerprints courants et décision explicite
  pour package sans images. Prêt après 17, 20 et 21.

### 23 - Purge, rétention, indicateurs disque et trace anonymisée

- Connu-inconnu : ancrage sur 7 jours, suppression et trace anonymisée ;
  brouillard sur concurrence purge/worker ; déni possible autour de fichiers
  résiduels ; abîme sur fuite par noms de fichiers ou chemins.
- Avocat du diable : la purge est un vrai sujet de cohérence, pas juste un
  `delete`.
- Résultat : renforcé avec purge non concurrente, idempotence et trace sans noms
  originaux ni chemins complets. Prêt après 22.

## Conclusion

Aucun ticket ne nécessite redécoupage immédiat. Les tickets 01, 05, 07, 08, 16,
18, 20, 22 et 23 demandent une attention de recette, mais pas une clarification
supplémentaire avant implémentation. Ils doivent être pris dans l'ordre et livrés
avec tests observables avant d'ouvrir les tickets aval.
