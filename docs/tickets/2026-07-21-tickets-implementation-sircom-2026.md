# Tickets d'implémentation Sircom 2026

Date : 2026-07-21

## Publication

Mode choisi : dossier Markdown local avec un fichier par ticket, car le dépôt ne
contient pas encore `docs/agents/issue-tracker.md` ni
`docs/agents/triage-labels.md`.

Index secondaire : `docs/tickets/2026-07-21-sircom-2026/README.md`.

Revue détaillée par ticket :
`docs/tickets/2026-07-21-sircom-2026/revue-connus-inconnus-avocat-du-diable.md`.

Statut cible initial des tickets : `ready-for-agent`.

Note post-revues GLM/SOL/Codex : après correction P0, seule la frontier
`{01}` est exécutable. Après livraison du ticket 01, le ticket 02 peut être
ouvert. Le ticket 03 et les tickets qui dépendent du schéma, du worker, du CSV,
des images ou de la purge ne doivent pas être ouverts avant la passe de décisions
listée dans `docs/2026-07-21-synthese-verification-globale-sircom-2026.md`.

Sources :

- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`
- `AGENTS.md`

Frontier initiale : ticket 01 uniquement.

## Règles globales

- Chaque ticket doit livrer un comportement observable.
- Ne pas créer toute l'arborescence cible avec des modules vides.
- Ne pas déplacer `sircom2026/excel_diagnostic.py` sans besoin immédiat.
- Ne pas utiliser `BackgroundTasks` FastAPI pour les traitements lourds.
- Ne pas coder en dur `B_ID`, `F_ID` ou une position Excel 2025.
- Ne pas commiter d'Excel réel, zip, image, log, rapport ou artefact généré.
- Les erreurs affichables sont structurées ; les logs techniques restent séparés.
- Les chemins disque internes ne sont pas exposés par l'API.

## Tickets unitaires

Chaque ticket vit dans son propre fichier pour tenir dans une session agent.

| N | Ticket | Dépend de |
|---|---|---|
| 01 | [Socle FastAPI, configuration, santé et UI shell DSFR](2026-07-21-sircom-2026/01-socle-fastapi-configuration-sante-et-ui-shell-dsfr.md) | aucun, peut commencer immédiatement. |
| 02 | [Politique d'accès locale et erreurs API structurées](2026-07-21-sircom-2026/02-politique-d-acces-locale-et-erreurs-api-structurees.md) | 01. |
| 03 | [Schéma SQLite, migrations et repositories de base](2026-07-21-sircom-2026/03-schema-sqlite-migrations-et-repositories-de-base.md) | 01. |
| 04 | [Lots, consultation, suppression logique et timeline UI](2026-07-21-sircom-2026/04-lots-consultation-suppression-logique-et-timeline-ui.md) | 02, 03. |
| 05 | [Store d'artefacts atomique et téléchargements par `artifact_id`](2026-07-21-sircom-2026/05-store-d-artefacts-atomique-et-telechargements-par-artifact-id.md) | 02, 03, 04. |
| 06 | [Statuts métier, événements, problèmes structurés et logs séparés](2026-07-21-sircom-2026/06-statuts-metier-evenements-problemes-structures-et-logs-separes.md) | 03, 04. |
| 07 | [Worker local, file SQLite, idempotence et annulation](2026-07-21-sircom-2026/07-worker-local-file-sqlite-idempotence-et-annulation.md) | 05, 06. |
| 08 | [Retry et invalidation aval par fingerprints](2026-07-21-sircom-2026/08-retry-et-invalidation-aval-par-fingerprints.md) | 07. |
| 09 | [Upload Excel sécurisé, limites et stockage artefact](2026-07-21-sircom-2026/09-upload-excel-securise-limites-et-stockage-artefact.md) | 05, 08. |
| 10 | [Diagnostic Excel persisté](2026-07-21-sircom-2026/10-diagnostic-excel-persiste.md) | 09. |
| 11 | [Messages Excel sale et panneau problèmes UI](2026-07-21-sircom-2026/11-messages-excel-sale-et-panneau-problemes-ui.md) | 06, 10. |
| 12 | [Mapping par défaut, profils brouillon et validation humaine](2026-07-21-sircom-2026/12-mapping-par-defaut-profils-brouillon-et-validation-humaine.md) | 11. |
| 13 | [Fusion multi-onglets](2026-07-21-sircom-2026/13-fusion-multi-onglets.md) | 12. |
| 14 | [Normalisation contenu](2026-07-21-sircom-2026/14-normalisation-contenu.md) | 13. |
| 15 | [Tri région/département et validation humaine](2026-07-21-sircom-2026/15-tri-region-departement-et-validation-humaine.md) | 14. |
| 16 | [Vérificateur de contrat CSV InDesign](2026-07-21-sircom-2026/16-verificateur-de-contrat-csv-indesign.md) | 14. |
| 17 | [Aperçu CSV, validation humaine et export UTF-16](2026-07-21-sircom-2026/17-apercu-csv-validation-humaine-et-export-utf-16.md) | 15, 16. |
| 18 | [Upload zip images et inspection sécurisée](2026-07-21-sircom-2026/18-upload-zip-images-et-inspection-securisee.md) | 05, 08. |
| 19 | [Spike formats images Mac/VPS](2026-07-21-sircom-2026/19-spike-formats-images-mac-vps.md) | 18. |
| 20 | [Matching et traitement images](2026-07-21-sircom-2026/20-matching-et-traitement-images.md) | 12, 18, 19. |
| 21 | [Rapports métier et technique](2026-07-21-sircom-2026/21-rapports-metier-et-technique.md) | 17, 20. |
| 22 | [Package final, manifeste et téléchargements](2026-07-21-sircom-2026/22-package-final-manifeste-et-telechargements.md) | 17, 20, 21. |
| 23 | [Purge, rétention, indicateurs disque et trace anonymisée](2026-07-21-sircom-2026/23-purge-retention-indicateurs-disque-et-trace-anonymisee.md) | 22. |

## Passe avocat du diable

### Cible relue

La cible de cette revue est le découpage en 23 tickets, pas les specs sources.
L'artefact adjacent le plus risqué est le futur ticket 01 : s'il part en grand
échafaudage applicatif ou en UI trop ambitieuse, tous les tickets suivants
hériteront d'une base instable.

### Steel-man

Le découpage est solide parce qu'il isole les zones qui cassent le plus souvent
dans ce type d'application : artefacts disque, idempotence worker, contrat CSV,
sécurité upload, mapping validé et purge. Il évite le découpage horizontal
backend/UI/tests et donne à chaque ticket une preuve observable.

Le choix de fichiers Markdown unitaires est adapté dans ce dépôt, car le tracker
local n'est pas encore formalisé. Les dépendances explicites suffisent pour
identifier la frontier et préparer des sessions `/implement` courtes.

### Préoccupations classées

1. Le ticket 01 peut gonfler en socle applicatif trop large.
   Sévérité : Moyenne. Statut : corrigée dans les tickets.
   Cadre : pré-mortem.
   Description : "UI shell DSFR" peut être interprété comme une vraie interface
   de production.
   Conséquence : le premier ticket devient long, difficile à tester et retarde
   la base FastAPI.
   Recommandation appliquée : le ticket 01 limite le périmètre à un shell Jinja
   / DSFR statique, aux routes santé, OpenAPI, configuration, limites visibles et
   manifeste `pyproject.toml`.

2. Les uploads doivent dépendre de l'invalidation aval.
   Sévérité : Haute. Statut : corrigée dans cette passe.
   Cadre : modes de défaillance.
   Description : un nouvel Excel ou un nouveau zip peut rendre obsolètes des
   étapes et artefacts déjà produits.
   Conséquence : l'application pourrait produire un package depuis des inputs
   incohérents.
   Recommandation : faire dépendre les tickets upload Excel et zip du ticket 08 et
   exiger l'invalidation aval dans leurs critères.

3. Le store d'artefacts dépend réellement des lots.
   Sévérité : Moyenne. Statut : corrigée dans cette passe.
   Cadre : clarification.
   Description : le téléchargement par `artifact_id` doit vérifier
   l'appartenance au lot, ce qui suppose le modèle de lot et ses routes.
   Conséquence : le ticket store pourrait tester un comportement isolé mais pas
   le vrai contrat de téléchargement.
   Recommandation : faire dépendre le ticket 05 du ticket 04.

4. Le ticket 19 est un spike et ne doit pas se transformer en feature implicite.
   Sévérité : Moyenne. Statut : bornée dans le ticket 19.
   Cadre : chapeau bleu.
   Description : HEIC, EXIF, profils couleur et dépendances système peuvent
   ouvrir un chantier trop large.
   Conséquence : le traitement images final dépendrait de comportements non
   prouvés ou variables Mac/VPS.
   Recommandation appliquée : le ticket 19 est un spike borné ; le traitement
   final reste dans le ticket 20.

5. La séparation rapports/package/purge est bonne, mais les frontières doivent
   rester strictes.
   Sévérité : Moyenne. Statut : corrigée dans les tickets.
   Cadre : cycle de vie des données.
   Description : les tickets 21, 22 et 23 manipulent tous les mêmes artefacts.
   Conséquence : risque de rapport incomplet, manifeste incohérent ou purge qui
   laisse des données métier.
   Recommandation appliquée : les tickets 21, 22 et 23 gardent des artefacts,
   noms de fichiers et critères de purge distincts.

6. Le tracker local reste une convention informelle.
   Sévérité : Basse. Statut : non bloquante pour la V1 locale.
   Cadre : processus.
   Description : `ready-for-agent` est textuel et non porté par un label réel.
   Conséquence : acceptable localement, mais fragile si les tickets migrent vers
   GitHub, Linear ou un tracker fichier par ticket.
   Recommandation optionnelle : créer `docs/agents/issue-tracker.md` et
   `docs/agents/triage-labels.md` seulement si le workflow ticket devient
   récurrent.

### Verdict avocat du diable

Verdict : Livrer avec modifications appliquées.

Le découpage reste bon. Les corrections nécessaires ont été intégrées :
dépendance du store aux lots, dépendance des uploads à l'invalidation, zip avec
sous-dossiers refusé clairement en V1 et socle FastAPI resserré autour d'un
manifeste de dépendances explicite.

## Analyse connu-inconnu

Reformulation : ce dossier transforme les trois specs Sircom 2026 en tickets
unitaires prêts pour agent. La question n'est plus "que construire", mais "ce
qui manque encore pour que l'implémentation démarre sans ambiguïté".

### Connus connus

- `[^]` La frontier initiale est le ticket 01 uniquement.
- `[^]` Les tickets couvrent FastAPI, SQLite, worker, artefacts, Excel, mapping,
  CSV, images, rapports, package et purge.
- `[^]` Les quatre risques prioritaires de la spec d'architecture ont des
  tickets dédiés : artefacts, worker, accès et CSV.
- `[~]` Le mode de publication est un dossier Markdown local, validé faute de
  tracker local formalisé.
- `[~]` Les données réelles restent hors tickets et hors Git.

### Connus inconnus

- `[~]` Stack frontend V1 : décision verrouillée pour les tickets, templates
  FastAPI/Jinja + DSFR statique et JavaScript minimal.
- `[~]` Authentification VPS réelle : hors périmètre des tickets V1, mais la
  frontière `AccessPolicy` doit éviter une refonte.
- `[~]` HEIC : décision bornée dans le ticket 19, sans support implicite.
- `[~]` Format des rapports : sections et noms V1 fixés dans les tickets 21 et
  22.
- `[~]` Validation InDesign réelle : hors périmètre automatisé, couverte par le
  vérificateur CSV et le package.

### Inconnus connus

- `[^]` "Ready-for-agent" peut pousser un agent à créer trop de fichiers vides
  pour satisfaire l'arborescence cible.
- `[^]` "Socle" peut devenir un ticket horizontal trop large si le premier
  agent dépasse les routes santé et le shell minimal.
- `[~]` Les tickets upload semblent simples, mais leur danger réel est
  l'invalidation des étapes aval.
- `[~]` Les critères UI minimaux peuvent être sous-testés sans capture ou test
  `TestClient` vérifiant les pages HTML.
- `[~]` Les futurs tickets images dépendront fortement de fixtures propres et
  non sensibles.

### Inconnus inconnus

- `[^]` Un fichier 2026 réel peut révéler une forme Excel non couverte par les
  tickets 09 à 13.
- `[^]` InDesign peut imposer une contrainte implicite non capturée par le CSV
  2025 de référence.
- `[~]` Le passage VPS peut introduire une contrainte de sécurité ou de stockage
  qui dépasse la V1 locale.
- `[~]` Les volumes images réels peuvent faire apparaître une pression disque ou
  mémoire non visible dans les fixtures.

### Risques prioritaires

1. `[^]` Respect du périmètre strict du ticket 01.
2. `[^]` Respect de l'invalidation avant tout upload ou artefact aval.
3. `[^]` Vérification CSV au niveau octets avant export.
4. `[~]` Exécution du spike image 19 avant traitement images.
5. `[~]` Formalisation éventuelle du tracker si le workflow dépasse ce dossier.

### Questions résolues pour la frontier actuelle

1. Frontend V1 : templates FastAPI/Jinja + DSFR statique.
2. Ticket 19 : spike borné avec note courte ou section de ticket mise à jour.
3. Tracker local : non requis avant ticket 01 ; à formaliser seulement si le
   workflow ticket devient récurrent.

### Verdict connu-inconnu

Verdict : Prêt pour implémentation progressive.

Les dépendances restantes sont des prérequis d'ordre entre tickets, pas des
blocages de cadrage pour agent. La frontier démarre au ticket 01.

## Passe finale tension LLM

Verdict : aucune tension LLM bloquante détectée dans les tickets unitaires.

- `Dépend de` décrit uniquement l'ordre d'exécution des tickets.
- Les décisions encore différées sont bornées par des tickets dédiés :
  authentification VPS hors V1, HEIC dans le ticket 19, rapport/package dans les
  tickets 21 et 22.
- Les tickets ne demandent pas à l'agent de choisir seul une architecture, une
  politique d'upload, un format CSV ou un format de package.
- Le seul point immédiatement exécutable reste le ticket 01.

## Couverture des specs

| Zone de spec | Tickets |
|---|---|
| FastAPI, OpenAPI, UI shell, config | 01 |
| Accès local et erreurs structurées | 02 |
| SQLite et états persistés | 03, 04, 06 |
| Artefacts disque | 05 |
| Worker, retry, annulation, invalidation | 07, 08 |
| Import et diagnostic Excel | 09, 10, 11 |
| Mapping et profils | 12 |
| Fusion et normalisation | 13, 14 |
| Tri et aperçu CSV | 15, 17 |
| Contrat CSV InDesign | 16, 17 |
| Zip images et sécurité upload | 18 |
| Environnement images | 19 |
| Matching et traitement images | 20 |
| Rapports et logs | 21 |
| Package final | 22 |
| Purge, rétention et disque | 23 |

## Hors périmètre global

- Authentification VPS réelle.
- Audit RGAA.
- Publication tracker externe.
- Celery/RQ/Redis.
- Plusieurs images principales par dossier.
- Traitement des images en sous-dossiers.
- Validation InDesign réelle automatisée.
