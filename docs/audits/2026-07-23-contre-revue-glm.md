# Contre-revue indépendante du code Made in France

Date : 23 juillet 2026

Contre-revue menée indépendamment du rapport interne
`docs/audits/2026-07-23-revue-code-fable-flavien.md`. Phase 1 à l'aveugle (verdict figé
avant lecture du rapport interne), puis phase 2 de croisement contradictoire.

Aucun fichier du dépôt n'a été modifié pour produire cette analyse, aucune
commande destructive lancée, aucune dépendance installée. Les preuves ont tourné
sur la suite `.venv` existante.

## 1. Verdict indépendant

Note finale : 15,3/20 (aveugle : 16/20 ; ajustée à la baisse après croisement,
voir section 4).

Le dépôt est nettement plus solide que ne le laissent entendre son README et son
TODO. C'est un socle FastAPI mature : worker à leases/fencing/invalidation par
empreinte, défense en profondeur sur les uploads, CSV InDesign fidèle et
auto-vérifié, 232 tests verts, 90,3 % de couverture réelle. La seule chose qui
peut casser l'application aujourd'hui sur une entrée réelle, ce sont les bornes
de ressources : un Excel aux dimensions extrêmes ou une image aux pixels
hors-norme peuvent suspendre ou saturer le poste local. Tout le reste est de
l'hygiène (dérive doc, gros modules, annulation tardive, dette 2025).

### Commandes exécutées et résultats décisifs

- `pytest --cov=sircom2026 -q -p no:cacheprovider` : 232 réussis, 4 ignorés,
  couverture 90,30 % (seuil 89), 8,96 s. Exit 0.
- `ruff format --check .` : 106 fichiers conformes. `ruff check .` : All checks
  passed. Exit 0 pour les deux.
- `git log` : 90 commits, historique de refactoring propre (extraction règles
  matching/mapping, rendu rapports, contrat lots, découpage template). Tags de
  livrables datés.
- Inspection `select_autoescape` (Starlette 1.3.1) : autoescape activé sur tous
  les `.html`.

## 2. Tableau de notation

| Critère | Note | Justification | Preuve locale |
|---|---:|---|---|
| Architecture et séparation | 3,3/4 | Factory, lifecycle, worker, artefacts, repositories `_database_*` bien isolés ; DAG d'invalidation clair. Routeur lots large mais fin. | app_factory.py:22, pipeline.py:6-37, worker_runner.py:59-93 |
| Maintenabilité, taille | 2,0/3 | 4 modules >900 lignes ; `api/lots.py` 1007 (25 endpoints) ; `image_matching.py` 1118 mêle matching et traitement image. Ruff propre, refactors en cours. | LOC confirmés ; api/lots.py:9-80 (imports massifs) |
| Robustesse, erreurs | 2,2/3 | Fencing/empreintes/transactions/réconciliation solides. Mais Excel non borné en dimensions, image non bornée en pixels/hauteur, annulation tardive sur le handler lourd. | excel_diagnostic.py:106 ; image_formats.py:81 + image_matching.py:803 |
| Tests, couverture | 2,6/3 | 90,3 % réel, E2E synthétique jusqu'au package, contrats figés. Trous ciblés sur les chemins de refus (excel_diagnostic 81 %) et conversion image. | couverture exécutée ; test_workflow_orchestration.py |
| Sécurité, données, secret | 1,6/2 | Upload whitelisté et borné, zip-slip refusé, host/origin/CSRF, policy default-deny, secrets absents. Manque : saturation locale (dims/pixels/disque) non traitée. | excel_upload.py:57-111, images.py:848-860, security.py:99-132 |
| UX, accessibilité | 1,5/2 | DSFR cohérent, statuts traduits, autoescape et textContent (pas de XSS), lang fr, skiplinks, labels. RGAA non audité (reconnu). `title` figé sur la page principale. | web_constants.py:140-158, app.js (textContent seul), index.html:7 |
| Documentation, exploitation | 1,2/2 | Specs riches (docs/specs). Mais README/TODO en fort retard sur le code ; README annonce « Python 3.x » contre `requires-python>=3.11` ; variables `SIRCOM_*` non documentées. | README.md:18-19, TODO.md:192-229, pyproject.toml:9 |
| Hygiène Git, CI, packaging | 0,9/1 | uv locked, CI verte, coverage et Playwright. Manque : `ruff check` (lint) non exécuté en CI (format seul) ; pas d'audit de dépendances. | ci.yml:32-33 |

## 3. Constats indépendants (par impact)

### Risques

1. Robustesse, modéré — Annulation non effective sur le handler le plus lourd.
   `run_image_matching_job` ne cède pas dans la boucle de conversion
   image-par-image ; seuls 5 points de progression grossiers existent.
   `WorkerCancelled` n'est levé qu'à la sortie du bloc heartbeat. Annuler un lot
   de centaines d'images revient à attendre la fin du batch. Fait :
   worker.py:472-474, image_matching.py:483-530 et 803-824.
2. Sécurité/robustesse, modéré — Bornes de ressources Excel et image
   insuffisantes. Aucun plafond lignes/colonnes/cellules sur l'Excel (seule la
   taille en octets est bornée) ; l'image est entièrement transposée et
   convertie avant un redimensionnement qui ne borne que la largeur. Un fichier
   petit mais extrême peut suspendre ou saturer. Fait : config.py (pas de cap
   dims), excel_diagnostic.py:106, image_formats.py:81-96, image_matching.py:807-813.
3. Robustesse, faible à modéré — Pression mémoire et disque. Le zip images
   traité est construit entièrement en `BytesIO` ; le disque n'est vérifié que
   par la readiness, pas avant un job lourd. Fait : image_matching.py:486,
   app_lifecycle.py:176.
4. Maintenabilité, faible à modéré — Modules volumineux à double responsabilité.
   `image_matching.py` mêle matching et traitement image ; `api/lots.py`,
   `mapping.py`, `web_ui.py` dépassent 980 lignes. Fait (LOC).
5. Documentation, modéré — Dérive README/TODO. Le README dit CSV/images/rapports
   et package « restent à brancher », or tout est branché. Le TODO marque
   matching, rapports, package et purge comme non faits alors qu'implémentés et
   testés, et contient même des lignes de revue étrangères au projet
   (TODO.md:242-244). Fait : README.md:18-19, TODO.md:192-229,
   worker_runner.py:59-93 (preuve que c'est branché).
6. Sécurité/fidélité, faible — Chaîne 2025 en dette séparée.
   `Image.MAX_IMAGE_PIXELS = None` (protection anti-bomb désactivée), pas
   d'orientation EXIF (la règle l'exige), chemins hardcodés
   `/Users/victoria/...`, `input()` bloquant, 10/13 scripts sans tests
   unitaires, hors CI. Fait : 10-process-images.py:373, 7-add_pathimg_excel.py:29,
   sircom_master_script.py:48 et 235.
7. Tests, faible — Branches métier peu couvertes. excel_diagnostic.py 81 %
   (chemins de refus 374-467), transform.py 86 %, package.py 86 %. Pas de bug
   démontré, mais couverture utile partielle sur les cas limites.
8. Mineur — `finish_failed` enregistre `error_message = error_code` (classe
   seule, perte du détail) : worker.py:425-426. `run_image_inspection_job` crée
   un `temp_dir` puis ne l'utilise pas : images.py:336-341. Excel bufferisé en
   RAM (50 Mo) alors que le zip est streamé : api/lots.py:223.

### Points forts réellement prouvés

- Suite verte et CI crédible : 232 réussis sur 236, 90,3 %, ruff propre, suite
  en 9 s (exécuté).
- CSV InDesign fidèle et auto-vérifié : écrit
  `BOM UTF-16 LE + encode("utf-16-le")`, vérifie la présence de BOM sinon
  erreur : csv_contract.py:85 et 337-341.
- Traitement image 2026 fidèle : EXIF transposé, fond blanc alpha
  (`Image.new("RGB",...,(255,255,255))` + paste masque A), ICC préservé,
  350 px LANCZOS q100 dpi300 : image_formats.py:84-95.
- Défense upload/zip en profondeur : whitelist extension, borne taille, zip-slip
  refusé, caractères de contrôle, sous-dossiers, doublons, entrées chiffrées,
  copie streamée sur disque : excel_upload.py:57-111, images.py:848-860.
- Worker mature : lease et fencing (`lease_version`), heartbeat thread,
  idempotence par clé, invalidation aval par empreinte, réconciliation au
  démarrage, expiry leases : worker.py:95-145 et 450-492, invalidation.py.
- Frontière locale défensive : policy default-deny sauf loopback, host-header
  strict, CSRF origin sur méthodes unsafe : security.py:71-132.
- UI sûre : statuts traduits pour l'affichage, aucune surface XSS (autoescape et
  textContent seul), lang fr, un seul h1, labels for/id, skiplinks, role=alert :
  web_constants.py:140-188, app.js.

Séparation fait / hypothèse / non vérifié : tout ce qui précède est un fait,
sauf « un Excel ou une image extrême peut saturer » qui reste une hypothèse
étayée (chemins d'allocation directs observés, scénario de saturation non
exécuté volontairement) et l'import réel dans InDesign 19.4+ qui est non vérifié.

## 4. Croisement avec la revue interne

Le rapport interne est précis, sourcé et honnête. Chaque citation a été vérifiée
en première main : toutes exactes. Verdict par point :

| Constat interne | Verdict | Preuve et nuance | Conséquence sur la priorité |
|---|---|---|---|
| Dimensions Excel non bornées | Confirmé | config.py n'a aucun cap lignes/colonnes ; seul `max_excel_mb` borne les octets. | Confirme la priorité 1. Angle mort sous-pondéré à l'aveugle. |
| Coût image non borné (pixels/hauteur) | Confirmé, nuancé | Préparation pleine image avant resize largeur-seule. En 2026, Pillow garde son `MAX_IMAGE_PIXELS` par défaut (backstop partiel), contrairement à la chaîne 2025 où il est désactivé. | Priorité haute maintenue. |
| Pression mémoire/disque | Confirmé | BytesIO complet + disque vérifié seulement en readiness. | Priorité haute. |
| Annulation tardive | Confirmé (constat 1) | worker.py:472-474 + boucle de conversion sans cession. | Priorité moyenne. |
| Routeur trop central | Confirmé, nuancé | 1007 lignes, mais chaque endpoint est un contrôleur fin qui délègue au domaine. Concentration d'imports plus que god-object. | Priorité basse (maintenabilité). |
| Recette visuelle non reproductible | Confirmé | `workflow-*-jeudi.yaml` liés à un « lot jeudi » local. | Priorité basse. |
| Oracle visuel faible | Confirmé | assert PNG et `len > 10_000` seul : test_lots_playwright.py:590-591. | Priorité basse. |
| Accessibilité (titre, focus erreur) | Confirmé | index.html:7 `<title>{{ app_name }}</title>` figé. | Priorité basse. |
| Documentation en retard | Confirmé (constat 5) | Plus incohérence Python 3.x contre 3.11. | Priorité moyenne. |
| Chaîne 2025 faible | Confirmé, enrichi | Ajout : `Image.MAX_IMAGE_PIXELS=None` (protection off) et EXIF absent, divergents de la règle métier. | Priorité basse à moyenne. |

### Ce que la revue interne a manqué

- 2025 : protection anti-bomb Pillow désactivée (`MAX_IMAGE_PIXELS = None`,
  10-process-images.py:373) et EXIF non appliqué alors que la règle
  (AGENTS.md:124) l'exige. Le constat interne 10 effleurait la 2025 sans ces deux
  points concrets.
- CI : `ruff check` absent (ci.yml:33 = format seul). Noté en Git 0,9, confirmé
  et relié au chantier recommandé.
- Confirmation autoescape : les statuts traduits sont cités, mais l'autoescape
  activé n'est pas explicitement confirmé. C'est ce qui clôt la question XSS (pas
  de surface réelle).
- `finish_failed` perd le détail d'erreur (worker.py:425-426) et temp_dir mort
  (images.py:336-341) : détails mineurs non listés.

### Ce que la revue interne a surestimé

- Routeur : la gravité « concentration » est exagérée. C'est une couche transport
  propre, pas un risque fonctionnel.
- Image : omettre le backstop Pillow (en 2026) rend le risque légèrement plus
  dramatique qu'il n'est. Réel, mais borné par défaut.

### Évolution de la note après croisement

Aveugle 16/20 puis final 15,3/20. Baisse principalement en Robustesse
(2,5 vers 2,2 : gaps Excel/image/disque sous-pondérés à l'aveugle), Sécurité
(1,8 vers 1,6 : saturation locale) et Git/CI (1,0 vers 0,9 : `ruff check`
absent). Les 15/20 internes et les 15,3/20 finaux convergent par des chemins
indépendants.

## 5. Angles morts

Faux positifs écartés (faillible, reportés puis réfutés) :

- « 500 brute sur date ISO `Z` » : `_parse_date_text` est entouré de
  `try/except ValueError` (transform.py:700-703), retourne `("", "invalid")`. Pas
  de crash.
- « ValueError sur `output_position` » : `assign_output_positions` ne produit que
  `int` ou `None` (mapping_rules.py:167-174), donc `int(... or 999_999)` ne peut
  pas lever.
- « 11 fuites de statut technique en UI » : les `if status == "bloque"` des
  templates sont du contrôle de flux, pas un affichage de statut brut. Les
  libellés visibles passent par `UI_STEP_STATUS_PRESENTATION`. La règle est
  tenue.
- « Surface XSS via `lot.title` » : autoescape activé (vérifié) et textContent
  seul, donc pas de surface.

Risques sous-estimés par la revue interne : la désactivation de la protection
Pillow en 2025 (réelle) et l'absence d'EXIF en 2025 (infidélité à la règle
métier).

## 6. Arbitrage des chantiers

| Chantier | Impact métier/op | Urgence | Réduction de risque | Effort | Blast radius | Réversible | Preuve attendue |
|---|---|---|---|---|---|---|---|
| A. Bornes ressources (Excel dims + image pixels/hauteur + résa disque + tests adversariaux + `ruff check` CI) | Élevé : évite suspend/saturation sur entrée réelle | Moyenne-haute | Élevée | Moyen | Contenu (upload/diag/image/worker) | Oui | Tests adversariaux exit code et assertions |
| B. Annulation effective handler lourd (cession par image) | Moyen : UX/ops, job suspendu | Moyenne | Moyenne | Faible-moyen | image_matching.py | Oui | Annulation observée avant N images |
| C. Découpage `api/lots.py` et gros modules | Faible : pas d'impact utilisateur | Faible | Faible | Moyen-élevé | API/structure | Oui | Tests restent verts |
| D. Réalignement doc (README/TODO/CHANGELOG et vars `SIRCOM_*`) | Faible-moyen : évite décisions sur info fausse | Moyenne (projet en audit) | Faible | Faible | Doc | Trivial | Relecture |
| E. Recette visuelle reproductible et oracle fort | Faible : filet de régression visuelle | Faible | Faible | Moyen | visual-tests | Oui | Scénarios autonomes et assertions de dimensions |
| F. 2025 : non-regression + EXIF + remettre `MAX_IMAGE_PIXELS` | Moyen : la 2025 est l'outil opérationnel aujourd'hui | Faible (remplacée par 2026) | Moyenne | Moyen | scripts-2025 | Oui | E2E 2025 minimal |

## 7. Chantier recommandé maintenant

Chantier A — Borner les ressources (Excel, images, disque) avec tests
adversariaux, et ajouter `ruff check` en CI.

Pourquoi celui-ci et pas un autre. C'est le seul chantier qui supprime un risque
de casser l'application sur une entrée réelle (pas un vecteur malveillant : un
`max_row` openpyxl surévalué par un formatage parasite, ou une image produits
très grande). Le chantier B (annulation) n'améliore que l'UX : le job finit
quand même et le lot reste supprimable. Le chantier D (doc) évite de mauvaises
décisions mais ne casse rien. Les chantiers C, E et F sont de l'hygiène. A est en
outre un prérequis à tout passage VPS : on n'expose pas un service sans bornes de
ressources. Enfin, il est borné, réversible et prouvable par tests.

Problème exact à résoudre. Aujourd'hui seuls les octets sont bornés. Un Excel
petit mais aux dimensions extrêmes, ou une image petite en octets mais énorme en
pixels, passe les filtres et fait osciller l'itération ou le décodage.

Périmètre minimal :

1. Excel : ajouter `SIRCOM_MAX_EXCEL_ROWS`, `SIRCOM_MAX_EXCEL_COLUMNS` (et
   cellules) dans `config.py` et `public_limits()` ; refuser tôt dans
   `validate_excel_upload` ou le diagnostic avec une erreur structurée
   (`SIRCOM_EXCEL_DIMENSIONS_EXCEEDED`) avant d'itérer. Cap par compteur
   d'itération réel, pas par `max_row` seul (openpyxl peu fiable).
2. Images : ajouter `SIRCOM_MAX_IMAGE_PIXELS` (et hauteur/largeur max) ;
   vérifier `.size` dès `Image.open` avant la transposition et conversion pleine
   image (`_convert_source_image_to_jpeg`) ; ne pas désactiver
   `Image.MAX_IMAGE_PIXELS` (le rendre configurable, définition cohérente
   2025/2026).
3. Disque : vérifier l'espace libre (`disk_free_min_mb` ou réservation par job)
   avant un job lourd (matching/package) ; refuser avec un problème structuré si
   insuffisant.
4. Tests adversariaux : Excel à dimensions extrêmes (refusé, pas de hang), image
   hors-pixels (refusée), cas proches des limites (acceptés), faible disque
   simulé (job bloqué).
5. CI : ajouter `uv run ruff check .` comme étape (gain quasi gratuit, ferme le
   gap Git/CI).

Fichiers probablement concernés : `config.py`, `excel_upload.py`,
`excel_diagnostic.py`, `excel_diagnostic_pipeline.py`, `image_formats.py`,
`image_matching.py` (`_convert_source_image_to_jpeg`), `images.py`
(`inspect_image_zip`), `app_lifecycle.py` ou `worker.py` (vérif disque pré-job),
`tests/` (nouveaux), `.github/workflows/ci.yml`.

Critères d'acceptation :

- Un Excel de 5 Mo déclarant 1 000 000 par 1 000 est rejeté en 422 sans suspendre
  le diagnostic.
- Une image de 40 000 px est rejetée avant décodage pleine résolution.
- Un état disque sous le seuil bloque le job lourd avec un problème métier (pas
  un 500).
- Les 232 tests existants restent verts ; couverture supérieure ou égale à 89 % ;
  `ruff check` passe en CI.

Tests et preuves attendus : nouveaux tests adversariaux (exit code 0 et
assertions de rejet) ; suite complète rejouée ; `ruff check` vert en local puis
en CI.

Hors périmètre volontaire : annulation effective (B), chantier séparé sans
dépendance ; découpage routeur (C) ; recette visuelle (E) ; chaîne 2025 (F) ;
VPS/Celery/SPA ; audit RGAA complet.

Risques d'implémentation :

- Un `MAX_IMAGE_PIXELS` trop bas rejette de vraies grandes photos produits :
  calibrer (mesurer d'abord les dimensions réelles du corpus Sircom, environ
  50 à 80 Mpx typique) et le rendre configurable.
- Les caps Excel ne doivent pas rejeter le vrai `Sircom.xlsx` (25 colonnes,
  petit) : seuils généreux (par exemple 200 000 lignes et 256 colonnes)
  sécurisés.
- `max_row` openpyxl peu fiable : cap par compteur réel d'itération, pas par la
  valeur déclarée.
- Le contrôle disque a une race (espace change entre contrôle et écriture) :
  best-effort acceptable.

## 8. À faire ensuite et à ne pas faire maintenant

Ensuite, dans l'ordre :

1. B — Annulation effective : passer le contexte à `build_processed_images_zip`
   et appeler `context.set_progress()` ou vérifier l'annulation toutes les N
   images. Effort faible, constat 1.
2. D — Réalignement doc : README/TODO/CHANGELOG à l'état réel du code et
   documenter toutes les variables `SIRCOM_*`, corriger « Python 3.x » en 3.11.
   Coût faible, le projet est en audit.
3. F (partiel) — Chaîne 2025 : remettre `Image.MAX_IMAGE_PIXELS`, appliquer EXIF,
   ajouter un E2E 2025 minimal de non-regression. La 2025 reste l'outil
   opérationnel actuel.
4. C puis E : découpage routeur et modules, puis recette visuelle reproductible
   avec oracle de dimensions.

À ne pas faire maintenant :

- VPS ou exposition réseau avant d'avoir fermé A (bornes ressources).
- Celery, Redis ou SPA (prématuré, la pile locale suffit).
- Réécrire la chaîne 2025 (la garder, la borner).
- Audit RGAA complet (utile seulement si une publication est envisagée).

## 9. Limites de la contre-revue

- Non exécuté : scénarios de saturation adversariaux réels (volontairement, aucun
  Excel ou image extrême construit). Impact : les gaps de ressources sont des
  hypothèses étayées (chemins d'allocation directs observés), pas des crashes
  démontrés.
- Non vérifié : import réel dans InDesign 19.4+ ; chaîne 2025 complète de bout en
  bout ; parcours complet au lecteur d'écran et au clavier ; audit CVE/SAST des
  42 dépendances.
- Non lus individuellement : les environ 1 090 fichiers DSFR vendoriés, les
  tickets `docs/tickets/`, et `transform.py`, `package.py`, `mapping.py`,
  `excel_diagnostic.py` couverts via un agent Explore (lecture d'extraits) puis
  calibrés par vérifications ciblées en première main (3 de ses « bugs » réfutés
  en relisant le code).
- Agents : deux audits `general-purpose` ont saturé leur contexte (lecture
  intégrale de gros fichiers), relancés en `Explore`, plus robustes. Leurs
  conclusions ont été calibrées (un faux positif « 11 fuites de statut » et deux
  « 500 brute » réfutés par lecture du code).
