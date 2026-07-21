# Spec : orchestration Sircom 2026

Date : 2026-07-21

Source principale : `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`, décisions Q80 à Q106.

## Énoncé du problème

L'interface web Sircom 2026 doit remplacer une chaîne 2025 composée de scripts
séquentiels et de fichiers intermédiaires par une orchestration web observable,
relançable et compatible avec des traitements lourds en tâche de fond.

Le Sircom doit pouvoir importer un Excel, valider le mapping, suivre le
traitement, comprendre les alertes, corriger les erreurs exploitables et exporter
un package final sans dépendre d'une requête HTTP longue ni d'un état implicite
dans le système de fichiers.

## Solution

Mettre en place un pipeline métier typé, semi-automatique et persisté en SQLite.
Chaque lot a des étapes visibles, des statuts en français, des problèmes métier
structurés, des logs techniques séparés et des artefacts stockés dans un dossier
par lot.

Les étapes sûres avancent automatiquement. Les points sensibles demandent une
validation humaine : mapping, tri, aperçu CSV et package final. Les traitements
lourds sont exécutés par un worker local intégré avec file SQLite.

## Récits utilisateurs

1. En tant qu'agent Sircom, je veux voir l'état de chaque étape du traitement,
   afin de savoir quoi corriger ou valider avant l'export.
2. En tant qu'agent Sircom, je veux que les alertes non bloquantes soient
   visibles sans empêcher le traitement, afin de produire le package même si des
   images ou valeurs sont absentes.
3. En tant qu'agent Sircom, je veux pouvoir supprimer immédiatement un lot, afin
   de limiter la conservation des données métier.
4. En tant qu'exploitant, je veux disposer de logs techniques séparés des
   problèmes métier, afin de déboguer sans exposer inutilement le contenu des
   fichiers dans l'interface.
5. En tant que développeur, je veux tester l'orchestration avec des Excels réels
   locaux et des Excels synthétiques, afin de vérifier les cas historiques et les
   cas limites sans données métier versionnées.

## Décisions d'implémentation

- Modèle d'orchestration : pipeline typé avec états persistés.
- Persistance structurée : SQLite local.
- Fichiers lourds : dossier d'artefacts par lot.
- Schéma SQLite opérationnel : `lots`, `etapes`, `jobs`, `artefacts`,
  `evenements`, `problemes`.
- Étapes visibles V1 :
  - `upload_excel`
  - `diagnostic_excel`
  - `mapping`
  - `fusion_multi_onglets`
  - `normalisation_contenu`
  - `previsualisation_csv`
  - `upload_images`
  - `traitement_images`
  - `package_final`
- Libellés UI des étapes : en français, par exemple `Prévisualisation CSV` pour
  `previsualisation_csv`.
- Statuts UI en français :
  - `non démarrée`
  - `prête`
  - `en cours`
  - `action requise`
  - `bloquée`
  - `terminée`
  - `terminée avec alertes`
  - `échouée`
  - `ignorée`
  - `annulée`
- Identifiants internes recommandés sans accents :
  - `non_demarre`
  - `pret`
  - `en_cours`
  - `action_requise`
  - `bloque`
  - `termine`
  - `termine_avec_alertes`
  - `echoue`
  - `ignore`
  - `annule`
- Déclenchement : pipeline semi-automatique. L'application avance seule sur les
  étapes sûres et attend une validation humaine pour mapping, tri, aperçu CSV et
  package final.
- Tâches de fond : worker local intégré avec file SQLite.
- Reprise : relance depuis l'étape échouée, avec invalidation automatique des
  étapes suivantes.
- Annulation : annulation coopérative entre sous-étapes. Le lot/job et l'étape
  active passent `annulé`; les étapes suivantes restent `non démarrée` ou
  `ignorée` selon le contexte.
- Alertes non bloquantes : l'étape passe `terminée avec alertes`, puis le
  pipeline continue jusqu'au prochain point de validation humaine.
- Validations humaines : statut `action requise`.
- Distinction de statut :
  - `bloquée` : correction utilisateur attendue.
  - `échouée` : erreur technique ou inattendue.
- Sévérités métier : `bloquant`, `alerte`, `information`.
- Problèmes métier : structurés par étape dans l'interface.
- Logs techniques : séparés des problèmes métier, disponibles pour debug.
- Refus Excel V1 : refus strict élargi pour cellules fusionnées, en-têtes
  multi-lignes, colonnes masquées, lignes masquées, onglets masqués, formules,
  absence ou ambiguïté `id_dossier`, doublons `id_dossier`, colonnes avec données
  sans en-tête, collisions de noms CSV après nettoyage.
- Doublons d'en-têtes source : alerte non bloquante, car la provenance complète
  `onglet + lettre colonne + nom original` permet de distinguer les colonnes.
- Format des messages Excel sale : message structuré avec titre, cause,
  emplacement, action à faire et détails techniques dépliables.
- Seuils V1 par défaut, configurables par variables d'environnement :
  - Excel : 50 Mo
  - zip images : 1 Go
  - nombre d'images : 1500
  - image unitaire : 50 Mo
  - taille décompressée maximale : 3 Go
- Conservation : 7 jours par défaut, configurable.
- Suppression manuelle : immédiate.
- Purge après suppression : supprimer uploads, artefacts, rapports et valeurs
  métier ; conserver seulement une trace technique anonymisée avec date, statut
  final, durées, tailles, compteurs et erreurs techniques sans contenu sensible.
- Suivi disque : indicateur global et par lot, incluant espace utilisé total,
  espace libre, lots les plus lourds, taille par lot, date d'expiration et alerte
  si un seuil disque est approché.

## Décisions de test

- Point testable : diagnostiquer `Sircom2.xlsx` comme importable quand le fichier
  réel local est présent.
- Point testable : diagnostiquer `Sircom1.xlsx` comme refusé quand le fichier
  réel local est présent, notamment à cause de colonnes masquées et formules.
- Point testable : générer des Excels synthétiques importables et refusés, sans
  données métier versionnées.
- Point testable : vérifier que chaque cause de refus Excel V1 produit un
  problème `bloquant` structuré avec titre, cause, emplacement et action.
- Point testable : vérifier que les doublons d'en-têtes source produisent une
  `alerte`, pas un blocage.
- Point testable : vérifier qu'une étape avec alertes non bloquantes devient
  `terminée avec alertes` et que le pipeline continue jusqu'au prochain point de
  validation.
- Point testable : vérifier qu'une validation humaine met l'étape en
  `action requise`.
- Point testable : vérifier qu'une relance depuis une étape échouée invalide les
  étapes suivantes.
- Point testable : vérifier qu'une annulation coopérative marque le lot/job et
  l'étape active `annulé`.
- Point testable : vérifier qu'une suppression manuelle purge les fichiers métier
  et conserve uniquement la trace technique anonymisée.

## Passe critique avocat du diable

### Steel-man

L'approche est raisonnable pour une V1 : SQLite réduit l'infrastructure, le
worker local évite les requêtes HTTP longues, et les étapes métier donnent une
surface claire pour l'interface et les tests. Le découpage garde la parité avec
la chaîne 2025 sans exposer les scripts historiques tels quels aux utilisateurs.

### Préoccupations

- Résumé : l'idempotence des jobs n'est pas encore spécifiée.
  Sévérité : Haute, bloquante avant implémentation du worker. Cadre : inversion
  et concurrence. Description : la spec dit qu'on peut relancer depuis une étape
  échouée, mais ne définit pas les clés d'idempotence, les verrous, les leases de
  jobs ni la stratégie si un clic ou un redémarrage lance deux fois la même
  étape. Conséquence : doublons d'artefacts, statut faux ou package généré depuis
  un état partiel. Recommandation : définir un contrat de job atomique avec
  `lot_id`, `step_id`, tentative, lease expirant, verrou de lot et écriture
  idempotente des artefacts.
- Résumé : la cohérence entre SQLite et les dossiers d'artefacts reste le point
  de panne principal.
  Sévérité : Haute, bloquante avant purge/package. Cadre : pré-mortem et cycle
  de vie des données. Description : l'état structuré est en base, mais les
  fichiers lourds vivent hors base. La spec ne dit pas quelle source gagne si le
  fichier existe sans ligne SQLite, ou l'inverse. Conséquence : purge incomplète,
  reprise impossible ou export utilisant un fichier obsolète. Recommandation :
  formaliser un registre d'artefacts obligatoire, des écritures en fichier
  temporaire puis promotion atomique, et une routine de réconciliation au
  démarrage.
- Résumé : l'invalidation aval est décidée mais pas contractualisée.
  Sévérité : Haute, bloquante avant mapping/preview/package. Cadre :
  questionnement socratique sur les implications. Description : quand l'Excel,
  le mapping, le tri ou les images changent, les étapes suivantes doivent être
  invalidées de façon déterministe. Conséquence : un utilisateur peut valider un
  aperçu périmé ou empaqueter des images qui ne correspondent plus aux données.
  Recommandation : définir un graphe de dépendances par étape, des empreintes
  d'inputs et un instantané du mapping/tri utilisé par chaque artefact.
- Résumé : les uploads ne sont pas encore traités comme une surface d'attaque.
  Sévérité : Haute, bloquante avant exposition web. Cadre : sécurité et cas
  limites. Description : zip images, noms de fichiers Excel, chemins internes,
  fichiers énormes, types MIME mensongers et archives à chemins relatifs peuvent
  viser le disque ou les logs. Conséquence : écriture hors dossier de lot,
  saturation disque, fuite de données ou crash reproductible par upload.
  Recommandation : imposer extraction sûre anti `zip slip`, bornes vérifiées
  avant extraction, normalisation des noms, validation d'extension et contenu,
  quotas par lot, et logs sans valeurs métier.
- Résumé : le refus strict Excel peut bloquer l'opérationnel le jour J.
  Sévérité : Moyenne, à surveiller. Cadre : pré-mortem UX. Description : la spec
  refuse des fichiers avec colonnes/lignes/onglets masqués et formules. C'est
  robuste, mais un export Démarches Simplifiées peut arriver sale sans capacité
  immédiate de correction par l'agent. Conséquence : support manuel urgent ou
  contournement hors application. Recommandation : prévoir un rapport de
  remédiation téléchargeable, des exemples de correction Excel, et un mode
  diagnostic sans import pour expliquer tous les blocages en une fois.
- Résumé : les seuils de volume sont définis, mais pas la stratégie de pression
  disque.
  Sévérité : Moyenne, à surveiller. Cadre : scalabilité et environnement.
  Description : 1 Go de zip et 3 Go décompressés sont acceptables pour un lot,
  mais la spec ne borne pas encore le nombre de lots concurrents ni la réserve
  disque minimale. Conséquence : le Mac local ou le VPS peut tomber en erreur en
  écrivant des artefacts intermédiaires. Recommandation : ajouter réservation
  d'espace avant job lourd, limite de jobs concurrents, refus préventif si
  l'espace libre passe sous seuil, et nettoyage des lots expirés avant traitement.
- Résumé : les questions ouvertes touchent encore des critères de fin essentiels.
  Sévérité : Moyenne, à surveiller. Cadre : chapeau blanc. Description : format
  du rapport, contenu exact du package et définition de `export testable` restent
  ouverts alors qu'ils conditionnent les tests d'acceptation. Conséquence : une
  implémentation peut être techniquement correcte mais non validable par le
  Sircom. Recommandation : traiter ces trois décisions avant de découper les
  tickets package/export.

Verdict : livrer avec modifications. La direction est bonne pour une V1, mais
les contrats d'idempotence, cohérence SQLite/fichiers, invalidation et sécurité
des uploads doivent être ajoutés avant de coder le worker et les endpoints de
traitement.

## Matrice connu-inconnu

### Connus connus

- La V1 cible un pipeline typé, semi-automatique, persisté en SQLite.
- Les fichiers lourds sont stockés dans un dossier d'artefacts par lot.
- Les étapes métier, statuts UI et sévérités métier sont décidés.
- Les points de validation humaine sont mapping, tri, aperçu CSV et package
  final.
- Les règles de refus Excel V1, de conservation, de suppression et de purge sont
  cadrées.
- Le corpus de validation combine Excels réels locaux et Excels synthétiques
  générables.

### Connus inconnus

- `[^]` Schéma SQLite précis : champs obligatoires, index, contraintes, clés
  étrangères, stratégie de migration et statut des tentatives.
- `[^]` Contrat d'exécution du worker : leases, verrouillage, idempotence,
  reprise après crash, annulation et gestion des jobs bloqués.
- `[^]` Contrat d'artefacts : chemins, empreintes, promotion atomique, source de
  vérité, réconciliation et purge.
- `[~]` Format exact du rapport téléchargeable et liste finale du package.
- `[~]` Définition de `export testable` et critères d'acceptation du CSV/package.
- `[~]` Contraintes d'authentification, accès local/VPS et exploitation.
- `[~]` Disponibilité réelle des conversions image, notamment HEIC/Pillow, sur
  Mac puis VPS.

### Inconnus connus

- `[^]` La simplicité de SQLite masque une exigence de discipline forte sur les
  transactions, verrous et reprises après crash.
- `[^]` La séparation problèmes métier/logs techniques masque le risque de
  fuite de données sensibles si les logs capturent des valeurs Excel ou noms
  d'images trop détaillés.
- `[^]` Le refus strict Excel suppose que les agents Sircom peuvent corriger le
  fichier source rapidement ou obtenir un nouvel export fiable.
- `[~]` Les Excels 2024/2025 sont utiles, mais ne prouvent pas que l'Excel 2026
  aura les mêmes anomalies, volumes ou conventions d'onglets.
- `[~]` Les libellés français côté UI et identifiants sans accents côté code
  supposent une table de correspondance maintenue et testée.
- `[~]` La conservation courte réduit l'exposition, mais peut compliquer le debug
  si un incident est découvert après purge.

### Inconnus inconnus

- `[^]` Un fichier réel 2026 peut combiner plusieurs anomalies acceptées
  séparément par les tests, par exemple onglet caché, colonnes sans en-tête,
  cellules avec dates ambiguës et IDs alphanumériques proches.
- `[^]` Un crash pendant une promotion d'artefact ou une purge peut laisser un
  état hybride que ni l'UI ni la relance ne savent interpréter.
- `[^]` Un zip peut contenir des noms Unicode, doublons après normalisation ou
  chemins piégés qui cassent le matching images sans être visibles dans les tests
  simples.
- `[~]` Un utilisateur peut supprimer un lot pendant qu'un job lourd travaille
  encore, révélant une course entre purge, annulation et écriture disque.
- `[~]` Le package peut être techniquement conforme mais inutilisable dans
  InDesign si les chemins, encodage, ordre des colonnes ou images renommées ne
  sont pas vérifiés ensemble sur un vrai scénario de bout en bout.

Risques prioritaires : idempotence du worker, cohérence SQLite/fichiers,
invalidation des étapes aval, sécurité des uploads, critères d'acceptation du
package final.

Verdict connu-inconnu : prêt sous conditions. Le cadrage suffit pour écrire une
spec d'implémentation, mais pas encore pour coder directement le worker et le
package final sans contrats complémentaires.

## Tensions à lever pour implémentation LLM

Cette section explicite les arbitrages pour éviter qu'un agent d'implémentation
résolve seul les ambiguïtés de la spec.

- `action requise` vs `bloquée` : `action requise` signifie que les inputs sont
  techniquement valides et qu'une décision humaine est attendue. `bloquée`
  signifie qu'une correction utilisateur est nécessaire avant de continuer.
- `bloquant` vs `bloquée` : `bloquant` est une sévérité de problème métier ;
  `bloquée` est un statut d'étape ou de lot. Une étape devient `bloquée` quand
  au moins un problème `bloquant` empêche la transition suivante.
- Étapes sûres vs validations humaines : les étapes automatiques ne doivent pas
  franchir les points `mapping`, tri, aperçu CSV et package final sans décision
  explicite. Une alerte non bloquante n'arrête pas l'automatisme avant le
  prochain point de validation.
- Refus Excel strict vs diagnostic utilisable : un Excel refusé ne doit pas être
  importé dans le pipeline de transformation, mais le diagnostic doit produire
  tous les problèmes détectables en une passe afin d'aider l'utilisateur à le
  corriger.
- Doublons d'en-têtes source vs collisions CSV : les doublons de noms source
  sont une `alerte` si la provenance les distingue. Les collisions après
  nettoyage en noms CSV finaux restent `bloquantes`.
- Suppression immédiate vs annulation coopérative : si un lot est supprimé
  pendant un job actif, la demande de suppression prend priorité, mais le worker
  doit arrêter proprement au premier point coopératif avant la purge finale. La
  purge ne doit pas courir en parallèle avec une écriture d'artefact.
- SQLite local vs déploiement VPS : la V1 suppose une seule instance applicative
  avec un seul writer SQLite. Ne pas implémenter implicitement du multi-instance,
  du multi-tenant ou une file distribuée.
- Logs de debug vs confidentialité : les logs techniques doivent permettre de
  diagnostiquer une étape, mais ne doivent pas contenir de valeurs métier issues
  de l'Excel, de contenu cellule, ni de chemins utilisateurs complets quand un
  identifiant de lot ou d'artefact suffit.
- Package final vs `export testable` : ne pas considérer le package terminé tant
  que les critères minimaux sont absents. Pour la V1, ces critères doivent
  couvrir au moins CSV UTF-16 BOM, séparateur virgule, LF, colonnes attendues,
  ordre attendu, `@pathimg`, images renommées et rapport produit.
- Génération d'artefacts vs validation humaine : toute validation humaine doit
  figer un instantané des inputs validés. Les artefacts aval doivent référencer
  cet instantané, pas relire implicitement l'état courant si l'utilisateur a
  modifié mapping, tri, Excel ou images entre-temps.

## Hors périmètre

- Moteur Celery/RQ avec Redis.
- Base serveur dès la V1.
- Authentification de production.
- Relance fine d'une sous-tâche isolée, par exemple une seule image.
- Tableau de bord complet d'observabilité.
- Modèle métier complet en tables dédiées pour chaque ligne, image ou mapping.
- Conservation longue des lots par défaut.
- Publication de cette spec dans un tracker externe.

## Questions ouvertes

- Format de stockage et portée des profils de mapping.
- Format exact du rapport téléchargeable.
- Liste exacte des fichiers du package final.
- Définition précise de `export testable`.
- Disponibilité HEIC/Pillow sur le Mac local puis sur le VPS.
- Contraintes d'authentification, stockage et exploitation du VPS interne.
- Contrat d'idempotence, verrouillage et reprise après crash du worker local.
- Contrat de cohérence entre SQLite, artefacts disque et purge.
- Graphe exact d'invalidation entre étapes et empreintes d'inputs.
- Règles de sécurité d'extraction zip et de normalisation des noms de fichiers.
- Seuils de pression disque globale, concurrence maximale et réservation
  d'espace.
- Transitions techniques exhaustives à formaliser dans les tests du module
  d'orchestration.

## Notes complémentaires

- Le dépôt ne contient pas `docs/agents/issue-tracker.md` ni
  `docs/agents/triage-labels.md`; la spec est donc publiée localement en
  Markdown.
- Les vrais fichiers Excel restent locaux et non committés.
- Les fichiers synthétiques doivent être générables à la demande et ne pas porter
  de données métier réelles.
- Les libellés UI sont en français ; les identifiants internes restent stables et
  sans accents.
