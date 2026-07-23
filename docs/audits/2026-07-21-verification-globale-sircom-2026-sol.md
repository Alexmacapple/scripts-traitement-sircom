> ## Décision actionnable
>
> - **Verdict :** STOP avant implémentation.
> - **Frontier exacte :** frontier déclarée `{01}` ; frontier effectivement exécutable `{}` tant que le contrat de configuration/readiness du ticket 01 n'est pas corrigé ; après cette correction documentaire, `{01}` ; après livraison acceptée de 01, frontier de graphe `{02, 03}`, mais aucun des deux tickets n'est exécutable sans sa correction ou son recadrage documenté en section 7.
> - **Nombre de corrections bloquantes :** 8.
> - **Nombre de corrections importantes :** 8.
> - **Nombre de corrections mineures :** 5.
> - **Fichiers à modifier avant ticket 01 :** `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`, `docs/specs/2026-07-21-orchestration-sircom-2026.md` et `docs/tickets/2026-07-21-sircom-2026/01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md`.
> - **Ticket 01 lançable maintenant :** non. Ses tests de valeurs par défaut n'ont pas d'oracle complet et son contrat `/health/ready` omet le seuil disque exigé par l'architecture. La correction est courte et ne remet pas en cause FastAPI/Jinja/DSFR.

# Vérification globale du cadrage Sircom 2026

Date : 2026-07-21

## 1. Verdict court

**STOP avant implémentation.**

Fait : le graphe de 23 tickets est complet au niveau des fichiers, cohérent entre
les deux index et acyclique. La seule racine déclarée est bien le ticket 01.

Jugement : le pack n'est pas encore globalement `ready-for-agent`. Il reste un
trou structurel entre images et CSV, ainsi que des contrats incomplets sur le
mapping, les transitions, le worker, l'invalidation, les artefacts et la purge.
Ces points changent le comportement observable ; ce ne sont pas des préférences
d'implémentation.

## 2. Résumé exécutif

1. Les décisions métier majeures du cadrage sont présentes dans les trois specs et
   presque toutes ont un ticket propriétaire.
2. Le défaut principal est une incohérence de séquencement : le ticket 17 valide
   le CSV final avant le traitement images du ticket 20, alors que le matching
   détermine `@pathimg` et que la valeur de `imageid` sans image retenue n'est pas
   tranchée par les sources 2026.
3. La règle normative de nommage des colonnes 2025 n'est portée par aucun critère
   d'acceptation de ticket.
4. Les tickets 06 à 08 citent statuts, leases, `run_id`, fingerprints et DAG,
   mais laissent encore à l'agent les transitions, le fencing des écritures et le
   graphe exact.
5. Les tickets images n'imposent ni worker, ni progression visible, ni annulation
   coopérative, malgré une règle verrouillée dans `AGENTS.md`.
6. La rétention de sept jours est décidée, mais aucun déclencheur de purge
   automatique, schéma de trace résiduelle ou comportement complet du seuil disque
   n'est assigné.
7. Les preuves locales sont bonnes pour l'Excel : 5 tests passent, `Sircom2.xlsx`
   est accepté et `Sircom1.xlsx` est refusé pour les causes attendues.
8. Aucun nouveau ticket n'est indispensable : les trous peuvent être fermés par
   un patch documentaire des specs et des critères des tickets existants.

## 3. Matrice de couverture : cuisine-moi/specs vers tickets

Légende : **couvert** = décision et preuve assignées ; **partiel** = propriétaire
identifié mais contrat incomplet ; **absent** = aucune responsabilité testable.

| Décision ou contrat source | Source précise | Ticket(s) | État | Preuve de couverture ou trou |
|---|---|---:|---|---|
| FastAPI, OpenAPI, Jinja/DSFR, local `127.0.0.1` | Architecture : 19-35, 64-82 ; contrat : 24-27, 58-70 | 01 | Partiel | Socle et tests présents, mais readiness disque/defaults incomplets au ticket 01:19-35. |
| Frontière d'accès locale, futur VPS sans SSO inventé | Contrat : 59-68 ; architecture : 101, 1008-1018 | 02 | Couvert | `ActorContext`, `AccessPolicy`, refus testable et auth VPS hors V1, ticket 02:7-27. |
| SQLite, six tables et état persistant | Cuisine-moi : 468-480 ; orchestration : 47-51 ; architecture : 502-625 | 03-08 | Partiel | Tables couvertes, mais `run_id`, état artefact, run des problèmes et contraintes atomiques manquent. |
| Store atomique et cohérence SQLite/disque | Architecture : 238-256, 627-653, 984-994 | 05 | Partiel | Détection de divergence au ticket 05:21-24 ; aucune réparation déterministe au démarrage. |
| Worker local, leases, idempotence, annulation | Cuisine-moi : 448-465 ; orchestration : 89-97, 162-180 | 07 | Partiel | Termes présents au ticket 07:13-25 ; TTL, renouvellement, reclaim, fencing et lifecycle app absents. |
| Retry, snapshots et invalidation aval | Cuisine-moi : 453-460 ; architecture : 727-742 | 08 | Partiel | Ticket 08:12-22 demande un graphe central, mais la source ne fixe que des exemples. |
| Upload Excel sécurisé et hors requête longue | Architecture : 668, 815-823 ; contrat : 72-90 | 09 | Partiel | Taille, archive et store couverts ; extensions exactes et pression disque non fermées. |
| Diagnostic strict, messages actionnables | Cuisine-moi : 403-411, 503-516 ; orchestration : 104-111 | 10-11 | Couvert | Causes V1, collecte des problèmes et UI sont assignées, sous réserve de remplacer la clause non déterministe du ticket 10:25-26. |
| `Sircom1.xlsx`, `Sircom2.xlsx` et synthétiques | Cuisine-moi : 408-411 ; contrat : 272-280 | 10 | Couvert | Tests locaux exécutés avec succès ; fichiers réels restent ignorés par Git. |
| Mapping par défaut, profils brouillon, provenance et validation | Cuisine-moi : 23-31, 278-281 ; architecture : 294-312, 764-788 | 12 | Partiel | Ticket propriétaire clair ; stockage/portée du profil, rôles logiques, renommage éditable et algorithme d'en-tête absents. |
| Fusion par union des `id_dossier`, une seule colonne ID | Contrat : 107-121 ; `AGENTS.md` : 107-109 | 13 | Partiel | Union et unicité couvertes ; ordre de première occurrence et timing de suppression des colonnes vides non définis. |
| Normalisation contenu, dates, texte sensible | Contrat : 141-153 ; `AGENTS.md` : 119-121 | 14 | Couvert isolément | Règles présentes au ticket 14:12-24 ; le contrôle final des colonnes devenues vides reste à raccorder. |
| Tri région/département et repli ordre Excel | Contrat : 154-157 ; cuisine-moi : 303-311 | 15 | Partiel | Validation humaine couverte ; détection et ordre Excel d'une union multi-onglets restent indéterminés. |
| CSV UTF-16 BOM, virgule, LF, guillemets, vides | `AGENTS.md` : 98, 114 ; contrat : 123-153 ; CSV réel | 16-17 | Partiel | Oracle octet présent ; endianness, nommage exact et séparation `csv_exportable` / `package_exportable` à fermer. |
| Référence CSV 2025 comme output, pas liste de colonnes | Cuisine-moi : 218-231, 343-346 ; contrat : 474-478 | 16 | Couvert | Ticket 16:20-24 distingue bien format et liste de colonnes. |
| Zip source libre, un par lot, images à la racine | Cuisine-moi : 108-116, 203-211 ; contrat : 170-182 | 18 | Partiel | Cas racine seul couvert ; zip mixte racine/sous-dossiers contradictoire. |
| Formats images et HEIC borné | Cuisine-moi : 113-116, 153-156 ; architecture : 1054-1063 | 19 | Couvert et volontairement borné | Le spike doit trancher support/refus/conditionnel avant ticket 20. |
| Matching, ambiguïtés, absences, JPG 350/100/300, EXIF | Contrat : 183-213 ; `AGENTS.md` : 123-125 | 20 | Partiel | Paramètres finaux couverts ; UI de résolution, tolérances complètes, erreurs et worker manquent. |
| Liaison image/CSV et sémantique de `imageid` / `@pathimg` | Cuisine-moi : 38-41, 128-131, 178-200, 378-381 | 17, 20, 22 | **Absent** | Aucun ticket ne produit le snapshot de liaison ni ne régénère le CSV après changement image ; seul le vide de `@pathimg` sans image est explicite, pas celui de `imageid`. |
| Rapport métier/technique séparé | Cuisine-moi : 363-371 ; contrat : 215-233 ; architecture : 412-430 | 06, 21 | Partiel | Formats et sections fixés ; IDs absents inter-onglets, colonnes supprimées et politique du nom original du zip à aligner. |
| Package exact et téléchargements par artefact | Architecture : 392-410, 954-960 ; contrat : 217-227 | 22 | Partiel | Liste exacte présente ; manifeste auto-référentiel et schéma du mapping utilisé non fermés. |
| Rétention, suppression immédiate, purge et trace anonymisée | Cuisine-moi : 473-485 ; orchestration : 118-125 | 23 | Partiel | Sept jours et purge manuelle couverts ; déclencheur automatique, trace dédiée et indicateurs complets absents. |
| UI à validations humaines, DSFR sans revendication RGAA | Orchestration : 25-27 ; architecture : 841-870 | 01, 04, 06, 11, 12, 15, 17, 20, 22 | Partiel | Mapping/tri/aperçu/package couverts ; actions annuler/retry/résoudre et progression ne sont pas toutes assignées à l'UI. |
| Données réelles hors Git, chemins internes non exposés | `AGENTS.md` : 85, 103 ; architecture : 1093-1094 | 02, 05, 09, 10, 18, 21, 23 | Partiel | Règles globales présentes ; réponse diagnostic et code public 403/404 à préciser. |

Conclusion de couverture : la présence d'un ticket par domaine ne suffit pas à
prouver la couverture comportementale. La matrice établit un manque complet
(`ImageBindings` vers CSV) et plusieurs couvertures partielles sur des invariants
de cohérence.

## 4. Findings classés par sévérité

### Bloquants

#### B1. La frontier déclarée n'est pas encore exécutable

**Fait.** L'architecture exige que `/health/ready` vérifie SQLite, le data dir et
l'espace disque (`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:67`
et `:662`). Le ticket 01 ne demande que la configuration, le data dir et
l'ouverture de SQLite « si le fichier existe »
(`docs/tickets/2026-07-21-sircom-2026/01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md:19`).
Il demande aussi des tests de defaults (`:34`) sans fixer
`SIRCOM_MAX_ACTIVE_JOBS` ni `SIRCOM_DISK_FREE_MIN_MB`, alors que la spec laisse
explicitement ces seuils ouverts
(`docs/specs/2026-07-21-orchestration-sircom-2026.md:361`).

**Risque.** Deux agents peuvent livrer des réponses 200/503 et des defaults
différents tout en cochant le ticket.

**Correction proposée, non appliquée.**

- Dans l'architecture, après la ligne 179, ajouter une table de defaults complète.
  Proposition cohérente avec le mode mono-worker : data dir
  `.sircom2026-data`, SQLite `<data-dir>/sircom.sqlite3`, bind
  `127.0.0.1`, port `8000`, worker activé, worker ID `local-1`, jobs actifs
  `1`, disque libre minimal `5120 MiB`.
- Dans l'orchestration, remplacer les lignes 361-362 par :
  « Seuils V1 : concurrence maximale `SIRCOM_MAX_ACTIVE_JOBS=1`, disque libre
  minimal `SIRCOM_DISK_FREE_MIN_MB=5120` et aucune réservation d'espace
  distincte. Ces defaults sont surchargeables, validés au démarrage et appliqués
  par `/health/ready`. »
- Dans le ticket 01, remplacer les lignes 19-20 par :
  « `GET /health/ready` retourne 200 seulement si la configuration est valide,
  le data dir est créable et inscriptible, une connexion SQLite `SELECT 1`
  réussit même au premier démarrage et l'espace libre est supérieur ou égal à
  `SIRCOM_DISK_FREE_MIN_MB`; sinon 503 avec code stable. Le schéma métier reste
  hors périmètre jusqu'au ticket 03. »
- Ajouter quatre tests : premier démarrage sans fichier SQLite, data dir non
  inscriptible, disque juste sous le seuil, disque au seuil.

Le choix `5120 MiB` est une recommandation de marge par rapport aux 3 Go
décompressés et au zip de 1 Go ; ce nombre doit être validé comme décision, pas
laissé à l'agent.

#### B2. Le cycle images vers CSV est contradictoire et sans propriétaire

**Fait.** L'absence d'image doit laisser `@pathimg` vide, décision Q24 corrigée
par Q73 (`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:129` et
`:380`). Ces décisions ne disent pas si `imageid` reste généré sans image
retenue ; la chaîne 2025 le génère depuis l'ID avant le matching
(`scripts-2025/2-image_id_adder.py:58`). Le ticket 17 produit et valide pourtant
le CSV final avant le ticket 20
(`docs/tickets/2026-07-21-sircom-2026/17-apercu-csv-validation-humaine-et-export-utf-16.md:5`
et `:19`). Le ticket 20 produit les JPG, mais aucun critère ne renseigne
`imageid` ou `@pathimg`
(`docs/tickets/2026-07-21-sircom-2026/20-matching-et-traitement-images.md:12`).
Le ticket 17 n'invalide le CSV que pour Excel, mapping et tri (`:21`), pas pour
un nouveau zip ou une résolution d'ambiguïté. Le ticket 22 ne contrôle que la
racine `@pathimg` (`22-package-final-manifeste-et-telechargements.md:21`).

**Risque.** Un package peut contenir un CSV validé avec des liaisons images
périmées, un chemin pour une image absente, ou des cellules vides alors qu'une
image a ensuite été retenue.

**Correction proposée, non appliquée.**

- Ajouter au design un snapshot versionné `ImageBindings`, une ligne par
  `id_dossier` : image source retenue ou absente, `imageid`, `@pathimg`, statut
  `matched|missing|ignored`, fingerprint et décision utilisateur.
- Fermer explicitement la sémantique de `imageid` sans image. Proposition de
  continuité 2025 : `imageid = dossier-{id-normalise}.jpg` pour toute ligne avec
  ID valide, même sans source retenue ; `@pathimg =
  {SIRCOM_INDESIGN_IMAGE_ROOT}/{imageid}` uniquement si une image est retenue,
  sinon `@pathimg` est vide. Cette proposition est un arbitrage produit, pas une
  règle déjà prouvée par le cadrage 2026.
- Faire dépendre le ticket 17 de 20, en plus de 15 et 16. Une action explicite
  « continuer sans images » met le flux images à `ignore` et produit un snapshot
  vide avant le ticket 17.
- Toute modification du zip, du matching ou d'une résolution invalide aperçu,
  CSV final, rapport et package.
- Renommer les deux gates : `csv_exportable` au ticket 17 et
  `package_exportable` au ticket 22. La checklist globale des lignes
  744-762 de l'architecture ne doit plus être utilisée par le ticket 17.

#### B3. Le contrat de mapping oblige encore l'agent à inventer

**Fait.** Le contrat impose le préfixe lettre Excel, les minuscules, la suppression
des accents et caractères spéciaux, puis 10 caractères maximum
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:134`). Le ticket 12
ne demande que de stocker le nom CSV et de bloquer les collisions
(`docs/tickets/2026-07-21-sircom-2026/12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md:14`
et `:26`). Le format et la portée de stockage restent déclarés `Unknown`
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:262`), et aucune table
de profil ne figure dans le schéma d'architecture. Les « types logiques confirmés »
du ticket 12:17 n'ont pas d'énumération.

**Risque.** Le mapping, la normalisation des dates, le tri et le matching images
peuvent employer quatre heuristiques incompatibles. Une collision multi-onglets
peut bloquer sans que l'utilisateur puisse renommer le champ.

**Correction proposée, non appliquée.**

- Ajouter au ticket 12 l'algorithme exact, avec tests `A`, `AA`, accents,
  ponctuation, troncature, collision et édition manuelle.
- Écrire explicitement les trois exceptions 2026 : `id_dossier`, `imageid`,
  `@pathimg`.
- Définir les rôles V1 :
  `id_dossier|date|region|departement|nom_image_source|siret|telephone|code_postal|code_administratif|texte`.
- Autoriser l'utilisateur à sélectionner, désélectionner, renommer dans la
  contrainte InDesign et confirmer un rôle logique.
- Persister les profils globaux V1 dans SQLite, sans valeur métier et hors purge
  de lot ; un profil compatible reste toujours un brouillon à valider. Ajouter la
  migration au ticket 12 si elle n'appartient pas au socle du ticket 03.

#### B4. L'état métier et le DAG d'invalidation ne sont pas fermés

**Fait.** La validation du tri est obligatoire
(`docs/specs/2026-07-21-orchestration-sircom-2026.md:86`) mais aucune étape
`validation_tri` n'existe dans la liste canonique (`:52`). Les transitions
décrivent la sémantique des statuts sans matrice exhaustive
(`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:711`). La section
d'invalidation ne donne que des exemples (`:727`) et omet le traitement images
après un changement de mapping (`:735`), alors que le matching dépend du mapping.
Le ticket 08 demande à l'agent de centraliser le graphe
(`docs/tickets/2026-07-21-sircom-2026/08-retry-et-invalidation-aval-par-fingerprints.md:14`)
sans lui fournir les arêtes ni la composition des fingerprints.

**Risque.** Un ancien aperçu, un ancien problème bloquant ou un ancien matching
peut rester courant après modification d'un input.

**Décisions structurantes à arbitrer, non appliquées.** Les exigences ci-dessous
définissent le contenu minimal du patch de décision ; elles ne constituent pas
encore une matrice ou un DAG prêt à copier tant que les transitions et arêtes
exhaustives ne sont pas validées.

- Ajouter l'étape `validation_tri` aux listes des specs et à la timeline du
  ticket 04, ou rattacher explicitement cette validation à une étape existante ;
  ne pas laisser les deux interprétations possibles.
- Publier une matrice `statut actuel + événement -> statut suivant` pour lot,
  étape et job, y compris invalidation, annulation et suppression.
- Publier toutes les arêtes du DAG. Au minimum, un changement Excel invalide tout
  l'aval ; un changement mapping invalide fusion, normalisation, tri, images,
  aperçu, CSV, rapports et package ; un changement image invalide bindings,
  aperçu, CSV, rapports et package.
- Définir les fingerprints par SHA-256 d'un JSON canonique versionné, avec la
  liste d'artefacts, décisions et versions de règles consommées par chaque étape.
- Les problèmes, événements et artefacts portent `run_id` et fingerprint ; seuls
  ceux du run courant peuvent bloquer ou être téléchargés.

#### B5. Le worker n'a pas encore de contrat d'exécution sûr

**Fait.** Le schéma `jobs` ne contient ni `run_id` ni clé d'idempotence
(`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:544`). Le ticket
07 exige lease, run et restart (`docs/tickets/2026-07-21-sircom-2026/07-worker-local-file-sqlite-idempotence-et-annulation.md:13`)
mais ne fixe pas TTL, renouvellement, reclaim, claim atomique, retry automatique
ou lifecycle `SIRCOM_WORKER_ENABLED`. L'architecture exige pourtant un writer
SQLite maîtrisé (`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:58`).

**Risque.** Deux workers ou un worker ancien peuvent publier un artefact ou
terminer une étape après expiration de lease.

**Décisions structurantes à arbitrer, non appliquées.** Les valeurs de TTL,
heartbeat, journal SQLite et busy timeout ne proviennent d'aucune source lue.
Elles doivent être choisies et publiées dans l'architecture et l'orchestration
avant de confier les tickets 03, 05 et 07 à un agent d'implémentation.

- Ajouter `idempotency_key`, `run_id`, `lease_version` et contraintes
  d'unicité « un job actif par lot/étape » au schéma.
- Fixer un TTL et un heartbeat configurables, horloge injectée, reclaim seulement
  après expiration, et compare-and-set sur `run_id + lease_version`.
- V1 : `SIRCOM_MAX_ACTIVE_JOBS=1` ; aucune relance automatique silencieuse ;
  l'action retry du ticket 08 crée une nouvelle tentative explicite.
- Fixer `PRAGMA foreign_keys=ON`, stratégie de journal SQLite, busy timeout et
  claim transactionnel ; tester deux connexions concurrentes.
- Le lifespan démarre exactement un poller si le worker est activé, aucun sinon,
  et effectue un arrêt gracieux testable.
- Ajouter les routes et preuves `POST .../cancel` et `POST .../retry`, avec
  202/404/409 déterministes et actions UI conditionnées par le statut.

#### B6. Le store détecte les incohérences mais ne sait pas les réparer

**Fait.** L'architecture demande une routine de réconciliation au démarrage
(`docs/specs/2026-07-21-orchestration-sircom-2026.md:178` et
`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:992`). Le ticket
05 demande seulement qu'un contrôle détecte fichier orphelin et ligne sans fichier
(`docs/tickets/2026-07-21-sircom-2026/05-store-d-artefacts-atomique-et-telechargements-par-artifact-id.md:23`).
Le modèle `artefacts` ne contient pas l'état `pending|committed|obsolete` ni
`run_id` (`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:566`).

**Risque.** La détection seule laisse l'application dans un état inutilisable ou
permet à un ancien worker de promouvoir un fichier après reprise.

**Correction proposée, non appliquée.**

- Ajouter `status`, `run_id`, `committed_at` et `obsolete_at` à
  `artefacts`.
- Définir le protocole : fichier temporaire, hash/flush, renommage atomique,
  compare-and-set du run courant, puis état `committed`.
- Fichier sans ligne : quarantaine/suppression, jamais adoption implicite. Ligne
  `committed` sans fichier ou hash invalide : `obsolete`, événement et problème
  technique.
- Test obligatoire : worker A expire, B reprend, A tente un commit tardif ;
  aucun artefact A ne devient courant ou téléchargeable.

#### B7. Les traitements images peuvent être livrés synchrones et sans progression

**Fait.** `AGENTS.md:122` impose tâche de fond et progression visible pour zip,
conversion et package. Les tickets 18 et 20 n'exigent ni worker, ni progression,
ni annulation (`docs/tickets/2026-07-21-sircom-2026/18-upload-zip-images-et-inspection-securisee.md:10`
et `20-matching-et-traitement-images.md:10`). Le ticket 22 impose le worker
(`22-package-final-manifeste-et-telechargements.md:13`) mais pas la progression.
L'absence totale de zip est autorisée par le contrat
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:179`), sans action
assignée pour marquer le flux images `ignore`.

**Risque.** Un agent peut satisfaire les tests de service tout en bloquant une
requête HTTP ou sans offrir de parcours pour continuer sans images.

**Correction proposée, non appliquée.**

- Tickets 18, 20 et 22 : upload HTTP borné puis 202 avec `job_id`; inspection,
  extraction, conversion et package par worker ; progression persistée et visible ;
  checkpoints d'annulation entre fichiers ; test prouvant que HTTP répond avant la
  fin.
- Ticket 20 : ajouter API/UI de résolution des ambiguïtés et action
  « continuer sans images », avec décision persistée, alertes et invalidation.
- Ticket 07 : exposer la progression courante/total/unité ; ticket 04 ou 06 :
  l'afficher dans la timeline sans faire varier la mise en page.

#### B8. Purge, disque et trace résiduelle ne forment pas un contrat exécutable

**Fait.** La rétention de sept jours et la suppression immédiate sont décidées
(`docs/specs/2026-07-21-orchestration-sircom-2026.md:118`). Le ticket 23 annonce
une purge planifiée mais ne donne aucun déclencheur
(`docs/tickets/2026-07-21-sircom-2026/23-purge-retention-indicateurs-disque-et-trace-anonymisee.md:7`).
Son indicateur disque se limite à « global et par lot » (`:17`), alors que la
spec exige libre, lots lourds, expiration et alerte seuil
(`docs/specs/2026-07-21-orchestration-sircom-2026.md:123`). La route DELETE de
l'architecture renvoie 409 pour job actif
(`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:667`), en
contradiction avec annulation puis purge au ticket 23:18-20.

**Risque.** La rétention peut n'être qu'une date affichée, les logs détaillés
peuvent survivre et une suppression pendant job peut avoir deux comportements.

**Décisions structurantes à arbitrer, non appliquées.** La cadence du purgeur et
la durée de la trace anonymisée ne sont pas décidées dans les sources. Les
propositions suivantes bornent le comportement, mais ces deux valeurs doivent
être fixées dans le contrat avant le ticket 23.

- `expires_at = created_at + retention` en V1, sans renouvellement silencieux.
- Scan des expirations au démarrage puis périodiquement selon un intervalle
  configuré ; purge idempotente et reprenable après crash.
- DELETE pendant job : 202, `purge_requested_at`, annulation coopérative, puis
  purge ; pas de 409.
- Ajouter une table `purge_traces` sans FK ni identifiant métier, avec allowlist
  `purged_at, final_status, durations, sizes, counts, error_codes` et durée de
  rétention explicitée ; supprimer le reste, logs détaillés inclus.
- `/api/storage` et UI : octets utilisés, octets libres, taille/expiration par
  lot, lots triés du plus lourd, seuil configuré et alerte ; tests au-dessous et
  au-dessus du seuil.

### Importants

#### I1. Les colonnes entièrement vides sont supprimées trop tôt

La règle source dit « après traitement »
(`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:325` et
`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:141`). Le ticket 13
supprime avant le ticket 14 (`13-fusion-multi-onglets.md:18`), alors qu'une
colonne de dates invalides peut devenir vide au ticket 14:15-16. Les colonnes
système encore vides peuvent aussi disparaître avant le contrôle du ticket 16:18.

**Correction proposée :** fusionner d'abord, normaliser ensuite, puis exécuter une
passe finale de suppression ; exempter `id_dossier`, `imageid` et
`@pathimg`. Ajouter un cas de colonne date entièrement invalide.

#### I2. « Ordre Excel » n'a pas de sens unique après union multi-onglets

Le contrat prend l'union sans feuille principale
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:111`) puis demande le
repli en ordre Excel (`:156`). Le ticket 15 reprend cette expression
(`15-tri-region-departement-et-validation-humaine.md:15`) sans départage.

**Correction proposée :** définir l'ordre stable de première occurrence :
onglets dans l'ordre du classeur, puis lignes dans chaque onglet ; conserver ce
rang comme départage du tri. Définir aussi normalisation de casse/accents et
valeurs vides en fin de tri.

#### I3. Le contrat d'upload/diagnostic Excel doit fermer formats et chemins

Le ticket 09 parle d'extensions valides sans liste
(`09-upload-excel-securise-limites-et-stockage-artefact.md:12`). Le ticket 10
demande tous les problèmes « quand c'est techniquement possible »
(`10-diagnostic-excel-persiste.md:25`). Le diagnostic existant contient un champ
`path` (`sircom2026/excel_diagnostic.py:74`) et le ticket 10 rend le résultat
consultable par API (`:27`), sans critère excluant ce chemin.

**Correction proposée :** V1 `.xlsx` uniquement, signature OOXML lisible ;
exécuter tous les contrôles indépendants et produire un problème structuré
`CHECK_SKIPPED` pour chaque contrôle impossible ; l'API expose `artifact_id`,
jamais le chemin local. Le nom original n'est conservé que selon la politique
rapport décidée.

#### I4. La route download peut révéler l'existence d'un autre lot

La matrice de routes prévoit 403 en cas de mismatch
(`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:679`), tandis que
le ticket 02 interdit de révéler les données d'un autre lot
(`02-politique-d-acces-locale-et-erreurs-api-structurees.md:20`).

**Correction proposée :** même réponse publique 404 et même code pour artefact
absent, supprimé, obsolète ou appartenant à un autre lot ; motif réel uniquement
dans un événement interne anonymisé. Ajouter un test d'indistinguabilité aux
tickets 02 et 05.

#### I5. Le contrat images perd des règles de matching et d'erreur

Le contrat exige nom sans extension, tirets/underscores, suggestion manuelle et
deux niveaux d'erreur (`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:193`
et `:212`). Le ticket 20 ne nomme que casse, espaces et « extension
équivalente » (`20-matching-et-traitement-images.md:14`) et n'exige pas l'écran
de sélection.

**Correction proposée :** définir une fonction de normalisation exacte et des
niveaux `exact|tolere|suggestion|ambigu`; jamais de seuil flou de similarité
automatique ; ajouter UI/API de sélection, message métier et événement technique
pour chaque échec de conversion. Ajouter une limite de pixels décodés pour les
images compressées.

#### I6. Rapport et nom original du zip ne sont pas alignés avec la confidentialité

Le rapport doit compter les IDs absents d'onglets et les colonnes supprimées
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:225`), mais le ticket
21:20-21 les omet. Le cadrage demande le nom original du zip dans logs et rapport
(`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:205`), alors que la
trace après purge interdit les noms originaux
(`23-purge-retention-indicateurs-disque-et-trace-anonymisee.md:23`).

**Correction proposée :** ajouter les deux compteurs au ticket 21 ; conserver le
nom original uniquement dans les métadonnées de lot et le rapport métier jusqu'à
purge, jamais dans les logs techniques ni la trace anonymisée.

#### I7. Le manifeste est auto-référentiel et le mapping final n'a pas de schéma

Le ticket 22 inclut `manifest.json` dans le package puis demande les empreintes
de tous les artefacts (`22-package-final-manifeste-et-telechargements.md:16` et
`:20`). Il nomme `mapping-utilise.json` sans définir son snapshot.

**Correction proposée :** le manifeste liste toutes les autres entrées mais
s'exclut de sa propre liste/hash ; `mapping-utilise.json` contient
`schema_version`, fingerprint du classeur, décision validée, provenance, rôle
logique, nom CSV, statut et position de chaque colonne.

#### I8. La confidentialité des logs arrive trop tard

Le ticket 06 sépare événements et problèmes, mais n'impose ni allowlist ni test
négatif (`06-statuts-metier-evenements-problemes-structures-et-logs-separes.md:17`).
Le test de fuite n'arrive qu'au ticket 21
(`21-rapports-metier-et-technique.md:28`), après uploads et worker.

**Correction proposée :** dès le ticket 06, définir une allowlist technique
(codes, durées, tailles, compteurs, IDs internes), interdire valeurs cellule,
noms/chemins originaux et ajouter des sentinelles sensibles dans les tests.

### Mineurs

#### M1. `id_dossier` n'est pas explicitement une exception dans toutes les sources

`AGENTS.md:112` applique la règle de préfixe sans exception ; le cuisine-moi ne
cite que `imageid` et `@pathimg` comme exceptions
(`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:275`). Le contrat et
les tickets exigent pourtant le nom final exact `id_dossier`
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:137`).

**Nouveau texte proposé :** « Exceptions 2026 : la clé logique exportée est
`id_dossier` ; les colonnes ajoutées sont `imageid` et `@pathimg`. »

#### M2. Une référence documentaire 2025 dit encore `#N/A`

`livrables-miweb-2025/livrables-miweb-1-2025/mapping_excel_csv.md:205` affirme
que les vides sont remplacés par `#N/A`, alors que le CSV réel contient 55
cellules vides et zéro `#N/A`, et `AGENTS.md:114` verrouille les cellules
vides.

**Correction proposée :** ajouter une note d'obsolescence à cette ligne :
« Observation documentaire historique contredite par l'artefact final ; pour
2026, les cellules restent vides. »

#### M3. `UTF-16 avec BOM` ne nomme pas explicitement l'endianness de l'oracle

Le CSV réel commence par `FF FE` et est UTF-16 little-endian, constat déjà écrit
dans le cuisine-moi (`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:220`).
Le ticket 16 ne dit que UTF-16 BOM
(`16-verificateur-de-contrat-csv-indesign.md:12`).

**Correction proposée :** « UTF-16LE avec BOM `FF FE`, conformément à l'oracle
2025 » et test rejetant UTF-16BE.

#### M4. Les specs gardent comme ouvertes des décisions désormais portées par ticket

Le contrat conserve les `Unknown` rapport/package/export
(`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:263`) alors que les
tickets 21 et 22 fixent les noms et le contenu. L'architecture garde « politique
V1 à confirmer » pour les sous-dossiers
(`docs/specs/2026-07-21-design-architecture-web-sircom-2026.md:379`).

**Correction proposée :** remplacer chaque entrée par `Résolu par ticket NN`
avec la règle finale, ou garder `Ouvert` et retirer le statut
`ready-for-agent` du ticket concerné.

#### M5. Le téléchargement séparé reste formulé comme une option flottante

Le contrat dit « Si possible » (`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md:218`)
et le ticket 22 « si disponibles » (`22-package-final-manifeste-et-telechargements.md:27`).

**Nouveau texte proposé :** « Confort optionnel V1 : chaque artefact déjà
`committed` peut être téléchargé séparément ; l'absence de ce confort ne bloque
pas l'acceptation du ticket 22. Le package complet reste obligatoire. »

## 5. Zones d'ombre restantes qui changent l'implémentation

Les inconnues volontairement bornées par un ticket ne figurent pas dans cette
liste : HEIC est borné par 19, l'authentification VPS est hors V1 derrière
`AccessPolicy`, et l'audit RGAA n'est pas revendiqué.

| Décision à fermer | Pourquoi elle change le code | Porte de sortie proposée | Échéance |
|---|---|---|---|
| Quand les liaisons images deviennent normatives pour le CSV | Change l'ordre du pipeline, les dépendances 17/20 et les invalidations | Snapshot `ImageBindings`, traitement/skip images avant validation finale CSV | Avant tickets 08, 17 et 20 |
| Valeur de `imageid` lorsqu'aucune image n'est retenue | Change le CSV et la fidélité à la chaîne 2025 | Proposition : conserver l'`imageid` déterministe et laisser seulement `@pathimg` vide ; inscrire la décision dans le contrat | Avant tickets 17 et 20 |
| Stockage et durée de vie des profils de mapping | Change schéma SQLite, migrations, purge et API | Profils globaux SQLite sans valeurs métier, hors purge des lots | Avant tickets 03 et 12 |
| Rôles logiques et édition des noms CSV | Change mapping, dates, tri, matching et résolution de collisions | Enum V1 fermée et édition contrainte dans le ticket 12 | Avant ticket 12 |
| Étape de validation tri et state machine | Change la timeline initialisée au ticket 04 et les transitions du ticket 06 | Ajouter `validation_tri` et une matrice d'événements/transitions | Avant tickets 04 et 06 |
| Contrat lease/fencing/reprise | Change tables, transactions, store et worker | `run_id` partout, lease versionnée, CAS, horloge injectée | Avant tickets 03, 05 et 07 |
| DAG et constituants des fingerprints | Change chaque endpoint de mutation et la validité des artefacts | Graphe exhaustif et JSON canonique versionné | Avant ticket 08 |
| Politique des zips mixtes | Change acceptation, extraction et rapport | Refuser toute image hors racine ; ignorer seulement une liste explicite de métadonnées système | Avant ticket 18 |
| Ancre/cadence de rétention et durée de la trace | Change scheduler, schéma, suppression et exploitation | Expiration depuis création, scan startup+périodique, table allowlist dédiée | Avant ticket 23 |
| Formats Excel V1 | Change validation upload et messages 415/422 | `.xlsx` OOXML uniquement en V1 | Avant ticket 09 |
| Comparateur région/département | Change ordre du CSV et golden tests | Rôles confirmés, comparaison Unicode/casse documentée, vides en fin, rang source comme départage | Avant ticket 15 |

## 6. Tensions LLM restantes

Le scan littéral des 23 tickets ne trouve aucune occurrence de
`à décider`, `à préciser`, `si possible`, `ou équivalent` ou
`faire au mieux`. Le corpus amont en conserve cependant, et plusieurs
équivalents sémantiques restent dans les tickets.

| Formulation exacte | Fichier et ligne | Risque | Correction proposée |
|---|---|---|---|
| « si le fichier existe » | Ticket 01:20 | Readiness verte au premier démarrage sans preuve SQLite | Toujours ouvrir la SQLite configurée ; 200/503 explicite |
| « contraintes d'unicité utiles » | Ticket 03:15 | Omission de la contrainte un job actif/run courant | Lister chaque contrainte et index attendu |
| « métadonnées minimales » | Ticket 05:15 | Store non interopérable entre tickets | Fermer les champs, états, run et version de schéma |
| « quand c'est techniquement possible » | Ticket 10:25-26 | Arrêt au premier problème ou contrôles sautés silencieusement | Tous contrôles indépendants ; `CHECK_SKIPPED` motivé |
| « types logiques confirmés » | Ticket 12:17 | Heuristiques divergentes dans 14/15/20 | Enum V1 normative |
| « clairement identifiables » | Ticket 15:12-13 | Tri automatique différent selon agent | Utiliser les rôles confirmés ; ambiguïté = action humaine |
| « ordre attendu » | Ticket 16:17 | Vérificateur circulaire ou oracle implicite | Ordre issu du snapshot mapping+tri validé |
| « prérequis export testable » | Ticket 17:17 | Checklist impossible avant tickets 20-22 | Remplacer par checklist `csv_exportable` exhaustive |
| « extension équivalente » | Ticket 20:14-15 | Matching faux positif | Normalisation exacte des suffixes et comparaison sans extension |
| « ressemblances partielles fortes » | Ticket 20:16-17 | Seuil de similarité inventé | Suggestion seulement ; aucune auto-sélection |
| « si nécessaire » | Ticket 20:19-20 | Package non invalidé après résolution | Toute modification de résolution invalide systématiquement l'aval |
| « bouton ou endpoint » | Ticket 23:13 | Deux parcours et sémantiques DELETE possibles | Fixer DELETE 202 + workflow de purge |
| « selon politique V1 à confirmer » | Architecture:379 | Zip mixte traité différemment | Écrire une politique unique et le test correspondant |
| « une trace [...] peut rester » | Architecture:652 | Conservation facultative contraire à Q93 | La trace allowlist est conservée selon une durée fixée |
| « Si possible » | Contrat fonctionnel:218 | Feature optionnelle interprétée comme obligatoire | Marquer explicitement confort non bloquant |
| « à préciser » pour l'auth VPS | Architecture:54 et :890 | Aucun risque V1 si la frontière est respectée | Garder, mais étiqueter `hors V1, ne bloque pas les tickets locaux` |

Les formulations historiques `À confirmer` du résumé cuisine-moi
(`docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md:8`, `:10`, `:11`)
sont résolues plus bas dans le même journal. Elles doivent être annotées
`résolu par Qxx` pour éviter une lecture partielle, mais ne constituent pas à
elles seules un blocage.

## 7. Vérification ticket par ticket

Règle de verdict :

- **prêt** : entrée, sortie, critères et preuve déterministes ;
- **à corriger** : architecture stable, critères ou texte incomplets ;
- **à recadrer** : une décision de cycle de vie, ordre ou sécurité doit être prise
  avant que l'agent puisse livrer un comportement unique.

Les 23 fichiers possèdent bien les six rubriques structurelles attendues :
`Statut`, `Dépend de`, `À construire`, `Critères d'acceptation`,
`Hors périmètre`, `Preuve attendue`.

| Ticket | Verdict | Motif et preuve |
|---:|---|---|
| 01 | **à corriger** | Defaults et readiness disque/SQLite incomplets, ticket 01:19-35 ; voir B1. |
| 02 | **à corriger** | Ticket correct, mais contradiction 403/404 avec architecture:679 ; voir I4. |
| 03 | **à recadrer** | Les champs « minimaux » de l'architecture n'incluent pas run, état artefact/problème ni contraintes atomiques, ticket 03:12-23 ; voir B4-B6. |
| 04 | **à corriger** | Parcours lot observable, mais timeline initialisée avant décision sur l'étape tri et DELETE ensuite redéfini, ticket 04:12-23. |
| 05 | **à recadrer** | Atomicité testée, mais réparation et fencing absents, ticket 05:12-24 ; voir B6. |
| 06 | **à recadrer** | Statuts présents, aucune matrice exhaustive ni contrat de logs sûr dès ce ticket, ticket 06:12-27 ; voir B4/I8. |
| 07 | **à recadrer** | Lease/run/restart cités sans protocole observable complet, ticket 07:13-25 ; voir B5/B7. |
| 08 | **à recadrer** | Le ticket demande à l'agent de créer le DAG et les fingerprints, ticket 08:14-22 ; voir B4. |
| 09 | **à corriger** | Upload/store/job clairs ; liste des formats et refus disque à fermer, ticket 09:12-24 ; voir I3/B8. |
| 10 | **à corriger** | Corpus et causes couverts ; collecte exhaustive et non-exposition du chemin à expliciter, ticket 10:12-27 ; voir I3. |
| 11 | **prêt** | Entrée diagnostic persisté, sortie UI actionnable et preuve synthétique fermées, ticket 11:7-30. |
| 12 | **à recadrer** | Algorithme d'en-tête, rôles, édition et persistance des profils absents, ticket 12:12-28 ; voir B3. |
| 13 | **à corriger** | Union testable, mais ordre source et suppression finale des vides incorrectement placés, ticket 13:12-22 ; voir I1/I2. |
| 14 | **à corriger** | Règles unitaires fermées ; il manque la passe finale de colonnes devenues vides, ticket 14:15-24 ; voir I1. |
| 15 | **à corriger** | Validation humaine couverte ; détection/comparateur et ordre union non déterministes, ticket 15:12-20 ; voir I2. |
| 16 | **à corriger** | Oracle octet solide ; ajouter nommage complet, UTF-16LE et source de l'ordre, ticket 16:12-24 ; voir B3/M3. |
| 17 | **à recadrer** | Gate global impossible et cycle images/CSV incohérent, ticket 17:5,17-23 ; voir B2. |
| 18 | **à recadrer** | Sécurité de base présente ; zip mixte, worker, progression et skip non fermés, ticket 18:12-27 ; voir B7. |
| 19 | **prêt** | Spike borné, issue explicite support/refus/conditionnel et preuve locale, ticket 19:7-31. L'inconnu HEIC est volontaire. |
| 20 | **à recadrer** | Conversion finale couverte ; producteur CSV, worker, progression, UI et niveaux de matching manquent, ticket 20:12-30 ; voir B2/B7/I5. |
| 21 | **à corriger** | Formats et sections fixes présents ; intégrité inter-onglets, colonnes supprimées et politique nom/log à compléter, ticket 21:12-30 ; voir I6/I8. |
| 22 | **à corriger** | Package exact et worker couverts ; bindings CSV, progression, manifeste et mapping snapshot à fermer, ticket 22:12-28 ; voir B2/I7. |
| 23 | **à recadrer** | Rétention/purge posées sans déclencheur, trace ni disque complets, ticket 23:12-26 ; voir B8. |

Total : **2 prêts**, **11 à corriger**, **10 à recadrer**.

### Dépendances

Faits déterministes :

- 23 nœuds, 36 arêtes ;
- aucune dépendance inconnue, aucun self-loop ;
- toute dépendance vise un numéro inférieur ;
- aucun cycle ;
- le README de dossier, l'index principal et les 23 champs `Dépend de` sont
  identiques.

Couches topologiques :

`{01} -> {02,03} -> {04} -> {05,06} -> {07} -> {08} -> {09,18} ->
{10,19} -> {11} -> {12} -> {13,20} -> {14} -> {15,16} -> {17} ->
{21} -> {22} -> {23}`.

La frontier **déclarée** `{01}` est correcte
(`docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md:26` et
`docs/tickets/2026-07-21-sircom-2026/README.md:7`). La frontier **exécutable**
est vide à cet instant parce que 01 est `à corriger`. Après correction B1, elle
redevient `{01}`. Après livraison de 01, le graphe ouvre `{02,03}`, mais 03
reste à recadrer tant que B4-B6 ne sont pas intégrés.

## 8. Recommandation finale

### Prochaine action concrète

Fermer le cadrage documentaire en deux lots, sans créer de nouveau ticket.

1. **Patch P0 avant tout code, court :**
   - compléter les defaults et `/health/ready` dans l'architecture ;
   - fermer la question des seuils V1 dans l'orchestration avec les mêmes valeurs ;
   - reporter le contrat exact dans le ticket 01 ;
   - relire uniquement ces trois diffs.

2. **Passe de décisions puis patch de fermeture avant d'ouvrir 03 et les tickets
   métier :**
   - specs orchestration/architecture : state machine, étape tri, schéma run-scopé,
     worker, DAG/fingerprints, bindings images, purge/disque ;
   - contrat fonctionnel : nommage/types/profils et distinction
     `csv_exportable` / `package_exportable` ;
   - tickets 02-23 concernés : reprendre les textes proposés B2-B8 et I1-I8 ;
   - mettre à jour le verdict trop affirmatif de
     `docs/tickets/2026-07-21-sircom-2026/revue-connus-inconnus-avocat-du-diable.md:17`
     et le statut `ready-for-agent` de l'index principal:16.

Ce second lot n'est **pas** un patch prêt à appliquer tel quel. Les valeurs de
lease/heartbeat, les transitions et arêtes exhaustives, la sémantique de
`imageid` sans image, la cadence de purge et la durée de la trace doivent d'abord
être arbitrées, puis inscrites comme texte normatif dans les fichiers propriétaires
indiqués en sections 4 et 5. Ne pas déléguer ces choix à un agent
d'implémentation.

Après le patch P0, **ticket 01 peut partir sans attendre le recadrage du cycle
images/CSV**, car son périmètre FastAPI/config/Jinja/DSFR n'en dépend pas. En
revanche, ne pas ouvrir le ticket 03 avant fermeture du schéma/run, ni les tickets
12/17/18/20/23 avant leurs décisions respectives.

Verdict après correction attendue : `GO ticket 01`, puis frontier
`{02,03}` sous réserve de la seconde passe.

## 9. Preuves

### Fichiers lus

Sources demandées, lues intégralement :

- `AGENTS.md` ;
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` ;
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md` ;
- `docs/specs/2026-07-21-orchestration-sircom-2026.md` ;
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md` ;
- `docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md` ;
- `docs/tickets/2026-07-21-sircom-2026/README.md` ;
- les tickets unitaires `01-*.md` à `23-*.md` ;
- `docs/tickets/2026-07-21-sircom-2026/revue-connus-inconnus-avocat-du-diable.md`.

Contexte lu :

- `README.md`, `TODO.md`, `CHANGELOG.md`, `.gitignore` ;
- `livrables-miweb-2025/livrables-miweb-1-2025/mapping_excel_csv.md` ;
- `livrables-miweb-2025/livrables-miweb-1-2025/structure_csv_analysis.md` ;
- `sircom2026/excel_diagnostic.py`, `sircom2026/synthetic_excels.py`,
  `tests/test_excel_diagnostic.py`, `scripts-2025/2-image_id_adder.py`.

### Commandes et résultats

| Contrôle | Commande ou méthode | Résultat |
|---|---|---|
| Inventaire | `rg --files`, `wc -l`, lectures `nl -ba` par plages | 23 tickets, 31 fichiers Markdown de cadrage/tickets examinés, plus contexte local |
| Graphe | Parse des tables Markdown et topological sort local | 23 nœuds, 36 arêtes, acyclique, frontier `{01}` |
| Cohérence index | Comparaison titres/dépendances index principal, README et fichiers | 0 divergence |
| Rubriques tickets | Contrôle des six sections requises | 23/23 conformes structurellement |
| Liens Markdown locaux | Résolution de 140 liens relatifs | 0 lien manquant |
| Tensions littérales | `rg -n -i` sur les formulations demandées | 0 occurrence des cinq expressions dans les tickets unitaires ; occurrences amont et équivalents listés en section 6 |
| CSV de référence | `xxd`, `file`, parseur `csv` Python sans afficher les valeurs | BOM `FF FE`, UTF-16LE, 10 lignes, 80 colonnes constantes, LF sans CRLF, 55 cellules vides, 0 `#N/A`, 0 `N/C`, en-têtes initiaux `a_madeinfr,b_id,imageid,@pathimg` |
| Tests diagnostic | `.venv/bin/python -m unittest tests.test_excel_diagnostic` | 5 tests passés |
| Excel réel importable | `.venv/bin/python scripts-2026/diagnose_excel.py livrables-miweb-2025/Sircom2.xlsx` | code 0, 4 onglets, onglet vide ignoré, fichier accepté |
| Excel réel refusé | même commande avec `Sircom1.xlsx` | code 1 attendu, refus pour colonnes masquées et formules |
| Données Git | `git ls-files` sur xlsx/zip/images/logs/csv et lecture `.gitignore` | aucun fichier de données réel suivi ; les deux Excels locaux sont ignorés |
| État Git final | `git status --short --branch` | branche `main` en avance de 3 commits ; seul `docs/2026-07-21-verification-globale-sircom-2026-sol.md` est attribuable à cette revue ; le document de prompt modifié et le rapport concurrent `-glm.md` ont été laissés intacts |
| Relecture indépendante | revue en lecture seule du rapport complet, puis contrôle ciblé après corrections | trois P1 initiaux et un P1 résiduel de cohérence corrigés ; verdict final : aucun P0/P1 |

Le premier essai des tests avec le `python3` système a échoué faute
d'`openpyxl`. Le nouvel essai avec l'environnement documenté `.venv` a
réussi. Ce n'est pas une preuve d'installation fraîche ; seulement une preuve que
l'environnement local existant fonctionne.

### Limites et non vérifié

- **Non vérifié :** import du package dans InDesign réel. Aucun package 2026 ni
  application n'existe encore.
- **Non vérifié :** support HEIC et écarts Pillow Mac/VPS. C'est volontairement
  borné par le ticket 19.
- **Non vérifié :** comportement du futur Excel 2026 réel, indisponible. Les
  Excels historiques et synthétiques ne prouvent pas sa structure.
- **Non vérifié :** worker, SQLite concurrent, purge, pression disque et
  téléchargements en runtime ; ils ne sont pas implémentés.
- **Non vérifié :** conformité RGAA/DSFR. Le cadrage interdit correctement de la
  revendiquer sans audit.
- **Non vérifié :** authentification, backup, TLS et multi-instance VPS ; hors V1.
- Aucune recherche web n'a été utilisée : les sources de vérité demandées sont
  locales.
- Aucun code applicatif, fichier de données, spec, ticket existant, commit ou
  remote n'a été modifié par cette revue.
