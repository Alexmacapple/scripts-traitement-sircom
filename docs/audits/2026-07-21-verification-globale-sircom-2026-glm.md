# Vérification globale du cadrage Sircom 2026

Date : 2026-07-21

Cible relue : la chaîne `cuisine-moi` -> `specs` (contrat fonctionnel, orchestration, design d'architecture) -> `tickets` (23 tickets unitaires + master + revue).

Objectif : décider si l'on peut passer à l'implémentation ticket par ticket sans trou majeur.

Méthode : lecture intégrale des 4 documents structurants, du master tickets, du README de dossier, de la revue dédiée et des 23 fichiers de tickets ; vérification de l'état réel du dépôt (code, données, CSV de référence) ; exécution du diagnostic existant sur les Excels réels ; matrices de couverture, de routes et de dépendances ; grep des tensions LLM.

## Décision actionnable

- Verdict : **GO ticket 01**. Le cadrage est complet, cohérent, implémentable et suffisamment cadré pour des agents d'implémentation. La chaîne `cuisine-moi -> specs -> tickets` est sans trou majeur. Deux clarifications IMPORTANTES (gabarit InDesign, règle de nettoyage des en-têtes) sont à planifier avant les tickets CSV (16/17/22), mais elles ne sont pas sur le chemin du ticket 01.
- Frontier exacte : **ticket 01 uniquement** (aucune dépendance ; graphe acyclique vérifié, feuille unique = ticket 23).
- Nombre de corrections bloquantes : **0**.
- Nombre de corrections mineures : **2 importantes** (pré-CSV, non bloquantes pour le ticket 01) + **5 mineures** (cosmétique ou précision).
- Fichiers à modifier avant le ticket 01 : **aucun**.
- Ticket 01 lançable maintenant : **oui**. Preuves d'état : pas de `pyproject.toml` (à créer par le ticket, cohérent) ; `.gitignore` sans `.sircom2026-data/` (à ajouter par le ticket, cohérent) ; aucun code FastAPI existant (à créer par le ticket) ; `sircom2026/excel_diagnostic.py` existe et reste hors périmètre du ticket 01. Les 12 critères d'acceptation du ticket 01 sont tous testables et ses sources sont liées.

## 1. Verdict court

`GO ticket 01`.

## 2. Résumé exécutif

Le cadrage Sircom 2026 est exceptionnellement dense et autodiscipliné : chaque spec porte sa propre passe avocat du diable, sa matrice connu-inconnu et sa section « tensions à lever pour implémentation LLM » ; le master tickets et la revue dédiée reproduisent l'exercice au niveau des tickets. La couverture est totale : chaque zone de décision du `cuisine-moi` (Q0 à Q106) est reprise par une spec et au moins un ticket, et les 21 routes de la matrice d'architecture ont toutes un ticket propriétaire. Le graphe des 23 tickets est acyclique, frontier = ticket 01, feuille unique = ticket 23. Les quatre risques bloquants nommés par la spec d'architecture (cohérence artefacts, idempotence worker, frontière d'accès, oracle CSV) ont chacun un ticket dédié avec critères explicites. Aucune tension LLM (« à décider », « si possible », « ou équivalent », « faire au mieux ») ne subsiste dans les contrats de tickets (vérifié par grep). Le CSV 2025 de référence est vérifié octet par octet (UTF-16 LE BOM, 0 CRLF, 80 en-têtes, 9 lignes, zéro `#N/A`/`N/C`, `imageid` position 3, `@pathimg` position 4) : toutes les affirmations des specs sont exactes. Le diagnostic Excel existant, exécuté frais, confirme `Sircom2.xlsx` acceptable et `Sircom1.xlsx` refusé. Deux sujets IMPORTANT restent à fermer avant les tickets CSV (16/17/22) : le couplage potentiel entre gabarit InDesign et noms de colonnes, et la règle de nettoyage des en-têtes non restituée comme critère testable. Aucun ne bloque le ticket 01.

## 3. Matrice de couverture : cuisine-moi / specs -> tickets

Lecture : chaque domaine de décision est porté par une spec et couvert par au moins un ticket. Aucune décision importante orpheline, aucun ticket orphelin.

| Domaine de décision | Spec porteuse | Ticket(s) | Couverture |
|---|---|---|---|
| Stack FastAPI, OpenAPI, UI shell, config, santé | Contrat fonc. + Design | 01 | complète |
| Frontière d'accès locale + erreurs API structurées | Design (avocat du diable n°3) | 02 | complète |
| SQLite, 6 tables, migrations, repositories | Orchestration + Design | 03, 04, 06 | complète |
| Lots, consultation, suppression logique, timeline UI | Contrat fonc. + Design | 04 | complète |
| Store d'artefacts atomique, téléchargement par `artifact_id` | Design (avocat du diable n°1) | 05 | complète |
| Statuts métier, événements, problèmes, logs séparés | Orchestration Q85/Q102-Q105 | 06 | complète |
| Worker local, file SQLite, idempotence, annulation | Orchestration Q87-Q89 + Design (n°2) | 07 | complète |
| Retry et invalidation aval par fingerprints | Orchestration Q88 + Design | 08 | complète |
| Upload Excel sécurisé, limites, stockage artefact | Contrat fonc. + Design (sécurité uploads) | 09 | complète |
| Diagnostic Excel persisté | Contrat fonc. Q78/Q99 + Design | 10 | complète |
| Messages Excel sale + panneau problèmes UI | Orchestration Q97-Q100 | 11 | complète |
| Mapping par défaut, profils brouillon, validation humaine | Contrat fonc. Q1/Q44/Q53 | 12 | complète (voir I2) |
| Fusion multi-onglets par `id_dossier` | Contrat fonc. Q45/Q57 | 13 | complète |
| Normalisation contenu (`<br>`, espaces, dates, texte sensible) | Contrat fonc. Q60/Q61/Q67/Q76 | 14 | complète |
| Tri région/département + validation humaine | Contrat fonc. Q58/Q59 | 15 | complète |
| Vérificateur de contrat CSV InDesign | Contrat fonc. Q65 + Design (n°4) | 16 | complète |
| Aperçu CSV, validation humaine, export UTF-16 | Contrat fonc. Q68 + Design (`export testable`) | 17 | complète |
| Upload zip images + inspection sécurisée | Contrat fonc. Q19/Q38 + Design (sécurité) | 18 | complète |
| Spike formats images Mac/VPS (HEIC, EXIF, ICC) | Cuisine-moi Q21/Q29 | 19 | complète (borné) |
| Matching et traitement images | Contrat fonc. Q4/Q25-Q27/Q33-Q36 | 20 | complète |
| Rapports métier et technique | Contrat fonc. Q69-Q71 | 21 | complète |
| Package final, manifeste, téléchargements | Contrat fonc. Q8 + Design | 22 | complète |
| Purge, rétention, indicateurs disque, trace anonymisée | Orchestration Q92-Q94 | 23 | complète |

Couverture des routes (matrice d'architecture, 21 routes) : les 21 routes ont un ticket propriétaire vérifié un à un (`/health*` et `/api/config/limits` -> 01 ; cycle de vie lots -> 04/23 ; downloads -> 05 ; excel -> 09/10 ; mapping -> 12 ; sort -> 15 ; csv -> 17 ; images -> 18/20 ; package -> 22 ; retry -> 08 ; cancel -> 07 ; storage -> 23). Aucune route orpheline.

Couverture des règles `AGENTS.md` verrouillées : fusion par `id_dossier` (13), une seule colonne `id_dossier` (12), CSV UTF-16 BOM/virgule/LF/vides (16/17), `imageid`/`@pathimg` après `id_dossier` (12), lignes sans `id_dossier` supprimées (13), colonnes vides supprimées (13), dates `dd/mm/yyyy` (14), zip racine + refus sous-dossiers (18), images JPG 350 px/q100/DPI300/fond blanc/EXIF (20), dossier `export-jpg-resize/` (20/22). Aucune règle verrouillée sans ticket.

## 4. Findings classés par sévérité

### Bloquant (0)

Aucun. La chaîne est implémentable depuis le ticket 01.

### Important (2) - à traiter avant les tickets CSV, hors chemin du ticket 01

**I1 - Couplage gabarit InDesign / noms de colonnes non adressé.**

- Fichier : `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md` lignes 125-139 (section CSV InDesign) ; `docs/cuisine-moi/...` Q74 lignes 383-386 ; Q56/Q57 lignes 293-301.
- Fait : la décision Q56/Q57 est délibérée et explicite : la colonne ID 2026 s'appelle `id_dossier` (exception métier), pas `b_id`/`f_id`. Le contrat fonctionnel (lignes 137-139) le confirme. Les en-têtes 2026 seront des noms nettoyés issus du mapping utilisateur, pas la liste 2025.
- Tension : Q74 (lignes 383-386) réduit le risque InDesign en s'appuyant sur le fait que « le CSV 2025 a été réimporté dans InDesign sans problème ». Mais cette évidence ne couvre que la fidélité de FORMAT (encodage, BOM, LF, séparateur). Elle ne couvre pas le changement d'IDENTITÉ des noms de colonnes : le publipostage InDesign mappe les champs par nom. Si le gabarit 2026 réutilise les champs 2025 (`b_id`, `a_madeinfr`, `c_email`...), le merge casse. Aucun document ne dit si le gabarit 2026 est nouveau ou réutilise les noms 2025.
- Risque pour l'implémentation : le critère « compatible InDesign » des tickets 16/17/22 n'est vérifiable que par fidélité de format ; la compatibilité réelle dépend d'un élément externe (le gabarit) non cadré. Si le risque se matérialise tard, il faut renommer des colonnes across tickets 12-17.
- Correction proposée (patch, à appliquer sur validation Alex) : ajouter dans `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`, section « Questions ouvertes » (après ligne 459), un item :
  ```
  - Couplage gabarit InDesign 2026 : confirmer avec le Sircom si le gabarit de
    publipostage 2026 référence les noms 2026 (`id_dossier` + noms nettoyés issus
    du mapping) ou réemploie les noms de champ 2025 (`b_id`, `a_madeinfr`, etc.) ;
    dans le second cas, prévoir un adaptateur de noms ou faire adapter le gabarit.
    La fidélité au FORMAT 2025 (Q73/Q74) ne couvre pas l'identité des noms de
    colonnes ; un test InDesign sur un échantillon reste le seul contrôle final
    (hors périmètre automatisé).
  ```
- Coût : une clarification Sircom + une ligne de spec. À planifier avant le ticket 16.

**I2 - Règle de nettoyage des en-têtes (Q52) non restituée comme critère testable.**

- Fichier : `docs/tickets/2026-07-21-sircom-2026/12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md` lignes 14-15 et 26 ; règle source : `docs/cuisine-moi/...` Q52 lignes 273-276, reprise dans le contrat fonctionnel lignes 134-136.
- Fait : la règle 2025 de renommage (« ajouter d'abord la référence de colonne Excel `A_`, `B_`... au nom original, puis minuscules, sans accents, sans caractères spéciaux, 10 caractères maximum ») est critique pour InDesign (Q52 : « InDesign casse le publipostage si cette convention n'est pas respectée »).
- Tension : aucun ticket ne restitue cette règle comme critère d'acceptation testable. Le ticket 12 mentionne « nom CSV » et « collisions après nettoyage » (ligne 26), le ticket 16 contrôle l'unicité et l'ordre des en-têtes, mais aucun ne pose l'algorithme de nettoyage ni son test. La règle n'est atteignable que par back-reference (« selon la règle 2025 ») dans les sources liées.
- Risque pour l'implémentation : un agent peut produire des noms nettoyés qui respectent l'esprit mais pas la convention exacte (ex. oubli du préfixe lettre, ou troncature incorrecte au-delà de 10 caractères), sans qu'aucun critère de ticket ni le vérificateur CSV (ticket 16) ne le rattrape. InDesign-critique.
- Correction proposée (patch) : ajouter un critère au ticket 12, après la ligne 15 :
  ```
  - [ ] Les en-têtes CSV finaux suivent exactement la règle 2025 : préfixe de la
        lettre de colonne Excel (`a_`, `b_`, ..., `aa_`), puis minuscules, sans
        accents, sans caractères spéciaux, longueur maximale 10 caractères ; un
        test couvre un nom avec accents et de plus de 10 caractères. `id_dossier`,
        `imageid` et `@pathimg` sont les seules exceptions (noms logiques ajoutés).
  ```
- Coût : un critère + un test. À planifier avant le ticket 12.

### Mineur (5)

**M1 - Spec d'architecture : politique zip sous-dossiers devenue stale.**

- Fichier : `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md` ligne 379.
- Fait : la ligne dit « sous-dossiers signalés selon politique V1 à confirmer ». La politique est désormais tranchée : refus en V1 (ticket 18, contrat fonctionnel lignes 177-178, cuisine-moi Q19, TODO ligne 44 cochée).
- Correction proposée : remplacer la ligne 379 par « sous-dossiers refusés en V1 (décision tranchée, voir ticket 18 : un zip dont les seules images sont en sous-dossiers est refusé avec message actionnable) ; ».

**M2 - Cuisine-moi : drapeaux et connus-inconnus partiellement obsolètes vs tickets.**

- Fichier : `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` lignes 586-594 (Connus inconnus) et 607-629 (Drapeaux ouverts).
- Fait : plusieurs items y figurent encore comme ouverts alors qu'ils sont résolus dans les tickets : format des profils de mapping (ticket 12), format du rapport (ticket 21), `export testable` (design spec lignes 744-762), politique zip sous-dossiers (ticket 18), HEIC (ticket 19). Un lecteur utilisant le cuisine-moi comme checklist les croira ouverts.
- Correction proposée : ajouter une note en tête de la « Matrice connu-inconnu consolidée » (après ligne 548) : « Les drapeaux et connus-inconnus ci-dessous sont un instantané du cadrage ; les résolutions finales (profils, rapport, `export testable`, zip sous-dossiers, HEIC) figurent dans `docs/tickets/2026-07-21-sircom-2026/` et la spec d'architecture ; ne pas les lire comme encore ouverts. »

**M3 - Propriété de la route `GET /images/status` implicite.**

- Fichiers : `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md` ligne 676 (route) ; tickets 18 et 20.
- Fait : la route `GET /api/lots/{lot_id}/images/status` est dans la matrice mais aucun ticket ne la revendique explicitement. Le bilan d'inspection (ticket 18) et le matching/ambiguïtés (ticket 20) couvrent le fond, mais le partage est implicite.
- Correction proposée (optionnelle) : ajouter au ticket 18 un critère « `GET /api/lots/{lot_id}/images/status` retourne le bilan d'inspection (zip valide, images à la racine, doublons, sans matching) » et laisser au ticket 20 la route de résolution d'ambiguïté.

**M4 - « Tri » : validation humaine sans `step_key` persisté.**

- Fichiers : `docs/specs/2026-07-21-orchestration-sircom-2026.md` lignes 52-61 (9 étapes, pas de « tri ») ; ticket 15.
- Fait : le tri est une validation humaine (Q86) et une décision persistée (ticket 15), mais ce n'est pas une des 9 `step_key`. C'est cohérent (porte de validation entre `normalisation_contenu` et `previsualisation_csv`), juste peu visible.
- Statut : observation, pas de correction nécessaire. La décision de tri est bien persistée et invalidée (tickets 08 et 15).

**M5 - Troisième Excel réel présent mais absent du corpus documenté.**

- Fichier : `livrables-miweb-2025/20240419_-_BDD_SIRCOM_CONCAT.xlsx` (3,4 Mo, présent sur disque).
- Fait : le corpus de validation (cuisine-moi Q79 lignes 408-411 ; contrat fonctionnel lignes 275-278) ne cite que `Sircom1.xlsx` et `Sircom2.xlsx`. Un troisième fichier réel existe et n'est ni référencé ni explicitement exclu.
- Statut : observation. Si ce fichier est un input pertinent, l'ajouter au corpus ; sinon le signaler comme hors corpus pour éviter une utilisation implicite.

## 5. Zones d'ombre restantes (qui changent l'implémentation)

Quatre seulement, et une seule est actionnable maintenant.

1. **Couplage gabarit InDesign (I1).** Seule zone d'ombre réelle pour les tickets CSV. Action : une clarification Sircom + une ligne de spec avant le ticket 16. Jusqu'à clarification, le critère « compatible InDesign » est interprétable.
2. **Vrai fichier Excel 2026 absent.** Structure, noms d'onglets, position exacte de `id_dossier` inconnus. Cette zone d'ombre est volontairement bornée : le corpus combine Excels réels 2024/2025 (non-régression) et Excels synthétiques générables (tests reproductibles). Ne bloque pas l'implémentation ; un fichier 2026 réel révélera des formes non couvertes (reconnu en « inconnu inconnu » dans toutes les specs). Non vérifié par défaut (le fichier n'existe pas).
3. **Support HEIC réel.** Borné par le ticket 19 (spike avec décision explicite alimentant les formats acceptés du ticket 20). Aucun traitement final ne dépend d'un support HEIC implicite. Vérifiable seulement au moment du spike.
4. **Authentification VPS.** Hors périmètre V1 ; la frontière `AccessPolicy`/`ActorContext` (ticket 02) évite une refonte. À préciser au moment du passage VPS, pas avant.

Les autres « inconnus » des specs (format du rapport, liste du package, `export testable`, stack frontend, politique zip sous-dossiers) sont désormais DÉCIDÉS dans les tickets ou la spec d'architecture ; ils ne sont plus des zones d'ombre pour l'implémentation.

## 6. Tensions LLM restantes

Vérifié par grep sur `docs/tickets/2026-07-21-sircom-2026/` et le master tickets : **aucun** terme « à décider », « à préciser », « si possible », « ou équivalent », « faire au mieux », « à définir », « à voir », « TBD », « à confirmer » dans les contrats de tickets exécutables. La passe anti-tension a porté ses fruits.

Restent 2 tensions résiduelles, toutes deux mineures et corrigibles par patch :

| Tension | Fichier | Ligne | Risque | Correction proposée |
|---|---|---|---|---|
| Back-reference « selon la règle 2025 » pour le nettoyage des en-têtes, sans restituer la règle | `12-mapping-...md` | 15, 26 | Un agent peut produire des noms nettoyés hors convention exacte ; InDesign-critique ; non rattrapé par le vérificateur CSV (ticket 16) | Ajouter le critère explicite (voir I2) |
| « sous-dossiers ... politique V1 à confirmer » stale | `design-architecture-...md` | 379 | Un agent lisant la spec peut croire la politique non décidée et inventorier un faux travail | Remplacer par « refusés en V1 (voir ticket 18) » (voir M1) |

Note : les « à définir / à préciser / à confirmer » restants dans le `cuisine-moi` sont légitimes (c'est un journal de cadrage ; ces drapeaux y documentent l'état au moment des questions et sont résolus plus loin ou dans les tickets). La spec d'architecture lignes 54 et 890 (« authentification à préciser ») est légitime : renvoi explicite au VPS, hors V1.

## 7. Vérification ticket par ticket

Verdict `prêt` (lançable après ses dépendances) sauf 12 qui demande un correctif mineur (I2) et 16/17/22 qui portent une note de risque (I1) sans besoin de recadrage.

| N | Ticket | Dépend de | Verdict | Note |
|---|---|---|---|---|
| 01 | Socle FastAPI, config, santé, UI shell DSFR | aucun | **Prêt (maintenant)** | Frontier. Preuves d'état vérifiées. |
| 02 | Politique d'accès locale + erreurs API | 01 | Prêt | |
| 03 | Schéma SQLite, migrations, repositories | 01 | Prêt | |
| 04 | Lots, consultation, suppression logique, timeline | 02, 03 | Prêt | |
| 05 | Store d'artefacts atomique + downloads | 02, 03, 04 | Prêt | Risque n°1 d'architecture bien couvert par les critères. |
| 06 | Statuts métier, événements, problèmes, logs | 03, 04 | Prêt | |
| 07 | Worker local, file, idempotence, annulation | 05, 06 | Prêt | Risque n°2 bien couvert (`run_id`, leases, pas de `BackgroundTasks` critiques). |
| 08 | Retry + invalidation aval par fingerprints | 07 | Prêt | Graphe centralisé + snapshots. |
| 09 | Upload Excel sécurisé + stockage artefact | 05, 08 | Prêt | Invalidation aval exigée. |
| 10 | Diagnostic Excel persisté | 09 | Prêt | Diagnostic existant exécuté frais : `Sircom2` acceptable, `Sircom1` refusé. |
| 11 | Messages Excel sale + panneau problèmes UI | 06, 10 | Prêt | |
| 12 | Mapping par défaut, profils brouillon, validation | 11 | **À corriger (mineur)** | Ajouter le critère de nettoyage des en-têtes (I2). |
| 13 | Fusion multi-onglets | 12 | Prêt | |
| 14 | Normalisation contenu | 13 | Prêt | Interdiction `nan`/`NaT`/`None`/`#N/A` explicite. |
| 15 | Tri région/département + validation humaine | 14 | Prêt | |
| 16 | Vérificateur de contrat CSV InDesign | 14 | Prêt | Risque I1 à documenter avant ; oracle 2025 = format, pas liste de colonnes. |
| 17 | Aperçu CSV, validation, export UTF-16 | 15, 16 | Prêt | Note I1 sur « compatible InDesign ». |
| 18 | Upload zip images + inspection sécurisée | 05, 08 | Prêt | |
| 19 | Spike formats images Mac/VPS | 18 | Prêt | Spike borné ; alimente le ticket 20. |
| 20 | Matching et traitement images | 12, 18, 19 | Prêt | |
| 21 | Rapports métier et technique | 17, 20 | Prêt | Format fixe (`rapport-metier.md`, `rapport-technique.json`). |
| 22 | Package final, manifeste, téléchargements | 17, 20, 21 | Prêt | Note I1 ; contenu exact fixé. |
| 23 | Purge, rétention, indicateurs disque, trace | 22 | Prêt | |

## 8. Recommandation finale

1. **Lancer le ticket 01 maintenant.** Aucun fichier à modifier avant ; preuves d'état vérifiées.
2. **Avant d'ouvrir le ticket 12** : appliquer le patch I2 (un critère + un test sur la règle de nettoyage des en-têtes).
3. **Avant d'ouvrir le ticket 16** : appliquer le patch I1 (une clarification Sircom : gabarit InDesign nouveau vs reuse 2025 ; une ligne de spec). C'est le seul élément externe non cadré qui touche au critère « compatible InDesign ».
4. **Patchs cosmétiques facultatifs quand voulu** : M1 (spec ligne 379), M2 (note en tête du cuisine-moi). M3/M4/M5 sont des observations, pas des bloqueurs.
5. **Tenir l'ordre des dépendances** : frontier = ticket 01, puis 02/03 en parallèle, etc. Le graphe est acyclique et la feuille unique est le ticket 23.

## 9. Preuves

### Fichiers lus (intégralité)

- `AGENTS.md` (source de vérité locale).
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` (629 lignes, Q0-Q106 + matrice).
- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md` (519 lignes).
- `docs/specs/2026-07-21-orchestration-sircom-2026.md` (375 lignes).
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md` (1233 lignes).
- `docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md` (master, 276 lignes).
- `docs/tickets/2026-07-21-sircom-2026/README.md`.
- `docs/tickets/2026-07-21-sircom-2026/revue-connus-inconnus-avocat-du-diable.md` (335 lignes).
- Les 23 tickets unitaires (01 à 23).
- `README.md`, `TODO.md`, `CHANGELOG.md` (contexte).
- `sircom2026/excel_diagnostic.py` (en-tête + structure des dataclasses).

### Commandes lancées et résultats

- `find docs` : cartographie complète (cuisine-moi, 3 specs, master, README dossier, 23 tickets, revue).
- Vérification de l'état réel : `sircom2026/excel_diagnostic.py` et `synthetic_excels.py` présents ; fixtures synthétiques présentes (7 xlsx) ; pas de `pyproject.toml` ; pas de code FastAPI (la mention FastAPI dans `excel_diagnostic.py` ligne 4 est un commentaire docstring, pas du code) ; `.gitignore` sans `.sircom2026-data/` ; CSV 2025 et `Sircom1/2.xlsx` présents.
- Vérification octets du CSV 2025 (`livrables-miweb-2025/livrables-miweb-1-2025/9-final-sircom-indesign-utf16.csv`) : 114966 octets ; BOM UTF-16 LE (FF FE) ; 0 CRLF ; 10 LF ; 80 en-têtes ; 9 lignes de données ; aucun `#N/A` ; aucun `N/C` ; `imageid` en position 3 ; `@pathimg` en position 4 ; premiers en-têtes `a_madeinfr`, `b_id`, `imageid`, `@pathimg`, `c_email`, `d_eigibili`. Conforme aux affirmations des specs.
- Exécution du diagnostic existant (preuve fraîche du ticket 10) : `Sircom2.xlsx` -> **ACCEPTABLE** (4 onglets, onglet vide `Avis` ignoré, `id_candidates` détectés `A:ID`/`A:Dossier ID`, région/département détectés) ; `Sircom1.xlsx` -> **REFUSE** (blockers : 2 colonnes masquées, formules détectées). Conforme à Q79, au CHANGELOG et au ticket 10.
- Grep tensions LLM sur tickets + master : 0 match (« à décider/préciser/définir/voir/confirmer », « si possible », « ou équivalent », « faire au mieux », « TBD »).
- Vérification des liens internes des tickets : 0 lien cassé.
- Graphe de dépendances (script) : acyclique ; frontier = [1] ; feuille unique = [23].

### Limites non vérifiées (honnêteté)

- **Exit code du diagnostic non capturé correctement** : la commande utilisait un tube vers `head`, donc le `$?` affiché (0) est celui de `head`, pas celui de Python. Le verdict sémantique (`ACCEPTABLE` / `REFUSE` + blockers) est lui bien lu dans la sortie. Le README indique un exit 1 pour un refus ; non revérifié ici sans tube.
- **Suite de tests du diagnostic non exécutée** : `tests/test_excel_diagnostic.py` existe mais n'a pas été lancée (`.venv/bin/python -m unittest tests.test_excel_diagnostic`). Inutile au verdict de cadrage : le diagnostic est du code 2026 déjà marqué terminé dans `TODO.md`, hors périmètre de cette vérification.
- **CSV 2025 décodé avec `utf-16` puis BOM strippé à la main** : le python3 système ne connaissait pas `utf-16-sig` ; contournement équivalent (vérification BOM sur les octets bruts + strip du caractère U+FEFF). Résultat identique.
- **Fichier Excel 2026 réel absent** : sa structure n'est pas vérifiable ; la couverture s'appuie sur le corpus borné (synthétiques + Sircom1/2), ce qui est la décision documentée.
- **Aucune vérification InDesign réelle** : hors périmètre (reconnu). La fidélité au format 2025 est le proxy ; le couplage gabarit/noms reste la zone d'ombre I1.
- **Patchs non appliqués** : conformément aux limites de la mission, aucune modification de fichier n'a été faite ; les corrections proposées sont livrées sous forme fichier/ligne/nouveau texte à valider par Alex.
