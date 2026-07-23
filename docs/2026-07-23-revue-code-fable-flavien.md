# Revue de code Made in France - mode Fable Flavien

Date : 23 juillet 2026

## 1. Verdict

**15/20.** Le socle 2026 est sérieux, testé et transactionnel. Il n'est
toutefois pas prêt à absorber sereinement les volumes configurés : les coûts
réels de décodage Excel et image restent insuffisamment bornés.

### Commandes décisives

- `pytest -p no:cacheprovider -q` : **232 réussis, 4 ignorés**, 8,55 s.
- Playwright hors bac à sable : **4 tests réussis**, 10,59 s. Le premier essai
  avait uniquement échoué sur l'interdiction d'ouvrir un port loopback.
- `ruff format --check .` : **106 fichiers conformes**.
- `ruff check .` : **aucune erreur**.
- `uv --no-cache lock --check` : verrou cohérent, **42 paquets résolus**.
- `gh run list` : CI du HEAD `edb61b5` terminée avec succès.
- `git status` final : aucun diff suivi ; seul le prompt d'audit préexistant
  reste non suivi.

## 2. Notation

| Critère | Note | Justification et preuve |
|---|---:|---|
| Architecture | **3,3/4** | Factory, lifecycle, worker et artefacts bien séparés ([`app_factory.py`](../sircom2026/app_factory.py#L22), [`worker.py`](../sircom2026/worker.py#L232)). Le routeur lots reste un point de concentration. |
| Maintenabilité | **2,0/3** | Ruff est propre et des règles ont été extraites, mais `api/lots.py` atteint 1 007 lignes et importe presque tous les domaines ([`lots.py`](../sircom2026/api/lots.py#L9)). Plusieurs modules dépassent 900 lignes. |
| Robustesse | **1,9/3** | Fencing, empreintes, transactions et réconciliation sont solides ([`artifacts.py`](../sircom2026/artifacts.py#L248)). Les bornes Excel/images et la réservation disque restent insuffisantes. |
| Tests | **2,7/3** | E2E synthétique jusqu'au package ([`test_workflow_orchestration.py`](../tests/test_workflow_orchestration.py#L191)), navigateur et seuil de couverture de 89 % en CI ([`pyproject.toml`](../pyproject.toml#L34)). |
| Sécurité | **1,4/2** | Contrôle Host/origine, refus du bind non-loopback, chemins confinés et erreurs masquées ([`security.py`](../sircom2026/api/security.py#L99)). Risques de saturation locale non traités. |
| UX et accessibilité | **1,5/2** | DSFR, français, liens d'évitement et tests mobile. Titre identique sur tous les écrans et restitution des erreurs perfectible ([`index.html`](../sircom2026/templates/index.html#L7)). |
| Documentation/exploitation | **1,3/2** | Specs riches, mais README et TODO ne reflètent plus l'implémentation actuelle ([`README.md`](../README.md#L13), [`TODO.md`](../TODO.md#L192)). |
| Git, CI, packaging | **0,9/1** | Dépendances verrouillées, CI verte, couverture et Playwright ([`ci.yml`](../.github/workflows/ci.yml#L29)). Le lint complet et l'audit de dépendances ne sont pas exécutés en CI. |

## 3. Top 10 des risques

1. **Dimensions Excel non bornées.** Le contrôle limite le fichier à 50 Mo,
   puis parcourt `max_row` et `max_column` sans plafond
   ([`excel_upload.py`](../sircom2026/excel_upload.py#L87),
   [`excel_diagnostic.py`](../sircom2026/excel_diagnostic.py#L106)). Un petit
   classeur aux dimensions extrêmes peut provoquer une boucle ou une allocation
   massive.
2. **Coût image non borné par pixels ou hauteur.** L'image complète est
   transposée et convertie avant redimensionnement, lequel ne borne que la
   largeur ([`image_formats.py`](../sircom2026/image_formats.py#L81),
   [`image_matching.py`](../sircom2026/image_matching.py#L803)).
3. **Pression mémoire et disque incompatible avec les limites annoncées.** Le
   zip traité est construit entièrement en `BytesIO`
   ([`image_matching.py`](../sircom2026/image_matching.py#L483)) ; le seuil
   disque n'est vérifié que par la readiness
   ([`app_lifecycle.py`](../sircom2026/app_lifecycle.py#L176)).
4. **Annulation tardive des traitements lourds.** Le heartbeat détecte
   l'annulation mais ne peut interrompre la boucle de conversion ; l'exception
   n'est remontée qu'à la sortie du handler
   ([`worker.py`](../sircom2026/worker.py#L470)).
5. **Routeur API trop central.** `api/lots.py` concentre modèles HTTP et
   orchestration de tous les domaines jusqu'à la ligne 1 007
   ([`lots.py`](../sircom2026/api/lots.py#L950)).
6. **Recette visuelle non reproductible.** Les scénarios utilisent un
   identifiant de lot local figé
   ([`workflow-excel-jeudi.yaml`](../visual-tests/pages/workflow-excel-jeudi.yaml#L10)).
7. **Oracle visuel trop faible.** Playwright vérifie seulement qu'un PNG dépasse
   10 Ko ([`test_lots_playwright.py`](../tests/test_lots_playwright.py#L589)).
   Une capture Excel de 33 829 px avec contenu répété a néanmoins été déclarée
   réussie.
8. **Accessibilité contextuelle incomplète.** Toutes les vues métier ont le
   titre navigateur `Sircom 2026` ; `showError()` affiche l'alerte sans déplacer
   le focus ni garantir sa visibilité
   ([`app.js`](../sircom2026/static/app.js#L24)).
9. **Documentation opérationnelle en retard.** Le README affirme encore que
   CSV, images, rapports et package restent à brancher, et annonce seulement
   « Python 3.x » alors que le package exige Python 3.11
   ([`README.md`](../README.md#L18),
   [`pyproject.toml`](../pyproject.toml#L9)).
10. **Chaîne 2025 faiblement protégée contre les régressions.** Elle reste
    annoncée comme opérationnelle, mais n'a pas d'E2E CI ; l'orchestrateur crée
    un environnement, installe des dépendances et écrit des logs
    ([`sircom_master_script.py`](../sircom_master_script.py#L253)).

## 4. Points forts prouvés

- Artefacts atomiques, vérification SHA-256, confinement des chemins et rejet
  des commits tardifs.
- Worker réellement conçu pour les leases, le fencing, l'idempotence et
  l'invalidation aval.
- E2E synthétique vérifiant CSV UTF-16, images, rapports, manifeste et package.
- Frontière locale défensive : Host, origine, loopback et 404 indiscernable pour
  les artefacts.
- Interface DSFR lisible, statuts métier traduits en français et tests
  desktop/mobile effectifs.

## 5. Priorités recommandées

### À faire maintenant

- Ajouter des plafonds Excel : lignes, colonnes, cellules, taille XML
  décompressée et temps de diagnostic.
- Ajouter des plafonds image : pixels, largeur, hauteur et mémoire estimée avant
  conversion.
- Produire le zip images directement sur disque et vérifier ou réserver l'espace
  avant upload et jobs lourds.
- Ajouter des tests adversariaux ciblant ces limites.

### À faire ensuite

- Découper `api/lots.py`, puis `image_matching.py`, `mapping.py` et
  `web_context.py`.
- Rendre les scénarios visuels autonomes avec fixtures créées au démarrage et
  vraies assertions de dimensions ou de régression.
- Contextualiser `<title>` et gérer explicitement le focus après erreur.
- Réaligner README, TODO, CHANGELOG et documenter toutes les variables
  `SIRCOM_*`.

### À ne pas faire pour l'instant

- Migrer vers Celery, Redis ou une SPA.
- Préparer le VPS avant d'avoir fermé les risques de ressources et de stockage.
- Réécrire la chaîne 2025 tant qu'une recette de non-régression minimale n'est
  pas disponible.

## 6. Limites de l'audit

- **Fait vérifié :** les absences de garde-fous citées sont observées dans le
  code ; les scénarios de saturation n'ont volontairement pas été exécutés.
- **Hypothèse étayée :** l'impact exact dépendra des volumes 2026 et des
  ressources du Mac, mais les chemins d'allocation sont directs.
- **Non vérifié :** import réel dans InDesign 19.4+, chaîne 2025 complète,
  données et livrables réels.
- **Non vérifié :** audit CVE externe des 42 dépendances et analyse SAST
  spécialisée.
- **Non vérifié :** parcours complet au lecteur d'écran et clavier manuel.
- Les 1 090 fichiers DSFR vendoriés et tous les tickets historiques n'ont pas
  été lus individuellement ; leur intégration et les fichiers applicatifs qui
  les utilisent ont été contrôlés.
