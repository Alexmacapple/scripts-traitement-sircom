# Post-mortem ShipGuard - Run MadeInFrance

Date : 2026-07-23

Destinataire : Loïc

Projet audité : `madeinfrance`

SHA MadeInFrance audité : `fbef50193daf08aebb0e70680ce288a4c738ea10`

SHA MadeInFrance après corrections : `784632e9bbb73ebca4cad6a87aa49b1888395650`

## Résumé exécutif

ShipGuard a été lancé en conditions réelles sur MadeInFrance, après les derniers
tickets de garde-fous ressources, CI, CodeGraph et documentation. Le résultat
est exploitable : les lanes process, crawl, visuel et review produisent des
artefacts cohérents, et le run remonte un risque applicatif réel que les tests
standards ne suffisent pas à qualifier entièrement.

La limite principale observée n'est pas côté MadeInFrance, mais côté
orchestration ShipGuard multi-agent : la lane audit n'a pas rendu de façon
déterministe sur toutes les zones. Un agent de zone a terminé, deux autres ont
dépassé le délai raisonnable, puis une sous-zone a été lancée. Le run a donc été
marqué partiel sur l'audit code, tout en conservant des findings vérifiés par
lecture locale et reproduction.

Verdict court : ShipGuard a été utile pour structurer un arbitrage technique et
a permis de fermer trois dettes applicatives concrètes. Son mode multi-agent
doit encore être mieux borné avant d'en faire un outil de décision quotidien
"PDG".

## Objectif du run

Relancer un vrai pipeline ShipGuard sur MadeInFrance, avec les dernières
modifications déjà poussées, pour vérifier si les chantiers récents sont
validables par une chaîne complète :

```text
code audit -> process check -> crawl -> visual run -> visual review
```

Le run était en mode audit et rapport. Aucun fichier applicatif ne devait être
modifié.

## Ce qui a été exécuté

### 1. Process checks

Commandes exécutées :

```bash
uv run --frozen --extra test ruff format --check .
uv run --frozen --extra test ruff check .
uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q
env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test python -m unittest tests.test_lots_playwright
```

Résultats décisifs :

```text
108 files already formatted
All checks passed!
245 passed, 5 skipped, coverage 90.51%
Ran 4 tests in 10.170s - OK
```

### 2. Crawl et visuel ShipGuard

Commande exécutée :

```bash
node /Users/alex/.codex/plugins/cache/shipguard/shipguard/2.6.3/cli/shipguard.mjs run --profile=sircom-smoke --serve
```

Résultats :

```text
crawl: 53 pages, 0 broken assets
visual: 7 manifests, 7 pass, 0 fail
review: visual-tests/_results/review.html
review server: http://127.0.0.1:54409/review.html
```

Manifests visuels passés :

| Manifest | Résultat |
|---|---:|
| `pages/accessibilite` | PASS |
| `pages/donnees-personnelles` | PASS |
| `pages/home` | PASS |
| `pages/plan-du-site` | PASS |
| `pages/workflow-excel-jeudi` | PASS |
| `pages/workflow-export-final-jeudi` | PASS |
| `pages/workflow-images-inspection-jeudi` | PASS |

### 3. Reproduction adversariale image

Un zip de 173 octets contenant une image PNG avec dimensions déclarées très
grandes a été injecté via le chemin API et worker.

Résultat mesuré :

```json
{
  "zip_bytes": 173,
  "declared_pixels": 178956971,
  "upload_status": 202,
  "worker_outcome": "failed",
  "inspection_step": "echoue",
  "status_endpoint": 409
}
```

Lecture : l'upload est accepté, puis le worker échoue techniquement pendant
l'inspection. Le comportement attendu serait un blocker métier structuré du type
image hors limites dimensionnelles.

## Artefacts générés

Les artefacts sont sous :

```text
visual-tests/_results/
```

Fichiers principaux :

| Fichier | Rôle |
|---|---|
| `run.json` | Statut agrégé des lanes |
| `audit-results.json` | Findings audit code |
| `process-results.json` | Résultats process |
| `process-report.md` | Rapport process lisible |
| `crawl-results.json` | Résultat crawl |
| `visual-results.json` | Résultat visuel |
| `findings.json` | Findings consolidés |
| `review.html` | Page de revue ShipGuard |

Ces fichiers sont ignorés par Git via `visual-tests/_results/`.

## Ce qui marche bien

### 1. Le pipeline visuel est exploitable

ShipGuard a correctement démarré l'application, crawlé les pages, capturé les
écrans et reconstruit la page de review. Les résultats sont lisibles et
actionnables.

### 2. L'agrégation des findings est utile

`findings.json` consolide les sources audit, process et annotation visuelle. Le
format est suffisamment clair pour distinguer un problème mesuré d'un signal
raisonné ou manuel.

Résumé final observé :

```text
findings total: 5
high: 2
medium: 2
low: 1
evidence: reasoned 3, measured 1, manual 1
```

### 3. ShipGuard a trouvé un vrai sujet produit

Le risque image bomb n'est pas cosmétique. Il concerne un petit fichier valide
capable de faire échouer un worker en erreur technique. C'est exactement le type
de signal qu'un outil d'audit doit faire ressortir après une série de tickets de
durcissement.

## Ce qui a été trouvé sur MadeInFrance

### High - `DecompressionBombError` échappe à l'inspection image

Preuves locales :

- `sircom2026/images.py:899` ouvre l'image avec `Image.open(handle)`.
- `sircom2026/images.py:905-915` intercepte plusieurs erreurs, mais pas
  `PIL.Image.DecompressionBombError`.
- `sircom2026/image_matching.py:832` a le même type d'ouverture avant
  conversion JPEG.

Impact : une image dont les dimensions déclarées dépassent le seuil Pillow peut
faire échouer le worker au lieu de remonter un blocker métier clair.

### Medium - Les limites globales du zip arrivent après des ouvertures image

Preuves locales :

- `sircom2026/images.py:487-492` inspecte les dimensions image par image.
- `sircom2026/images.py:511-516` vérifie ensuite le nombre total de fichiers,
  le nombre d'images et la taille décompressée totale.

Impact : un zip manifestement hors limites peut encore déclencher des coûts
d'ouverture image avant d'être refusé pour dépassement global.

### Low - Le diagnostic Excel direct charge le workbook avant garde locale

Preuves locales :

- `sircom2026/excel_diagnostic.py:445` charge le workbook en `read_only=False`.
- Le chemin web a toutefois un pré-check en `read_only=True` dans
  `sircom2026/excel_upload.py:95-110`.

Impact : risque plus faible sur le parcours web normal, mais dette résiduelle
sur l'appel direct du diagnostic.

## État après correction MadeInFrance

Les trois findings applicatifs ci-dessus ont été traités et poussés.

| Finding | Statut | Commit | Preuve |
|---|---|---|---|
| `DecompressionBombError` non convertie en erreur métier | Corrigé | `027dfad` | `DecompressionBombError` devient `SIRCOM_IMAGE_DIMENSIONS_EXCEEDED` dans l'inspection zip et la conversion. |
| Limites globales zip appliquées après ouvertures Pillow | Corrigé | `027dfad` | Les bloqueurs zip globaux sont évalués avant l'inspection dimensionnelle des images. |
| Diagnostic Excel direct dépendant du préfiltre upload | Corrigé | `784632e` | `diagnose_workbook()` préflight en `read_only=True` avant tout chargement complet. |

CI GitHub vérifiée :

- `027dfad` - `Handle Pillow image bombs as business blockers` :
  `https://github.com/Alexmacapple/scripts-traitement-sircom/actions/runs/30010934717`
- `784632e` - `Preflight Excel dimensions before full diagnostic load` :
  `https://github.com/Alexmacapple/scripts-traitement-sircom/actions/runs/30011364866`

Preuves locales relancées sur le dernier état :

```text
uv run --frozen --extra test ruff format --check . -> 108 files already formatted
uv run --frozen --extra test ruff check . -> All checks passed!
uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q -> 249 passed, 5 skipped, coverage 89.90%
env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test python -m unittest tests.test_lots_playwright -> 4 tests OK
```

## Point faible ShipGuard observé

La lane audit multi-agent n'a pas terminé proprement.

Déroulé :

- `sg_audit_infra_worker` a terminé et écrit `zone-z01-r1.json` avec 0 bug.
- `sg_audit_excel` n'a pas rendu dans le délai.
- `sg_audit_images_e2e` n'a pas rendu dans le délai.
- Une relance plus ciblée a encore dépassé le délai.
- Une sous-zone a été lancée pendant la relance, ce qui a augmenté la dérive
  au lieu de réduire le périmètre.
- Les agents restants ont été interrompus pour éviter un run indéfini.

Le run a donc été marqué :

```json
{
  "audit": {
    "status": "ran",
    "partial": true,
    "reason": "one zone agent completed; two zone agents interrupted after timeout; root supplied verified findings"
  }
}
```

Ce point ne remet pas en cause les résultats process, crawl, visuels ni les
findings vérifiés localement. Il dit en revanche que l'orchestration audit n'est
pas encore assez déterministe pour un usage de pilotage sans supervision.

## Analyse : ShipGuard ou contexte local ?

Les deux jouent probablement, mais à des niveaux différents.

### Ce qui relève du contexte local

- La conversation était longue.
- Le dépôt contient beaucoup de contexte d'audits précédents.
- Le scope demandé était large : "vrai pipeline complet".
- Les zones Excel et images demandent une lecture métier non triviale.

Ces facteurs peuvent amplifier les temps de réponse des agents.

### Ce qui relève de ShipGuard comme produit

Même dans ce contexte, un outil d'audit devrait borner explicitement :

- le budget par zone ;
- la profondeur de délégation ;
- le format de rendu partiel ;
- la cause finale d'un run incomplet ;
- la séparation entre findings produits par agents et findings complétés par
  l'opérateur racine.

Le problème n'est donc pas "ShipGuard ne marche pas". Le problème est plutôt :
ShipGuard marche, mais son mode audit multi-agent doit être plus prévisible
quand une zone bloque.

## Demandes produit proposées à Loïc

### 1. Timeout et budget explicites par zone

Chaque zone devrait avoir un budget visible, par exemple :

```text
zone_timeout_sec
max_files_per_zone
max_findings_per_zone
```

À expiration, ShipGuard devrait écrire un artefact partiel plutôt que laisser
l'orchestrateur deviner l'état.

### 2. Artefact partiel obligatoire

Même si l'agent n'a pas terminé, il devrait produire un JSON minimal :

```json
{
  "zone": "images",
  "status": "timeout",
  "files_started": 4,
  "files_completed": 2,
  "findings": [],
  "last_file": "sircom2026/images.py",
  "reason": "zone_timeout"
}
```

Ce serait beaucoup plus exploitable qu'un silence.

### 3. Option `max_agent_depth=1`

Dans un audit de décision, les sous-agents spontanés peuvent rendre le run moins
lisible. Une option de profondeur maximale permettrait de forcer :

```text
root -> zones uniquement
```

Sans sous-zone interne.

### 4. Statut final plus tranché

La sortie finale devrait afficher sans ambiguïté :

```text
SHIPGUARD RESULT: COMPLETE | PARTIAL | FAILED
audit: partial - 2/3 zones completed
process: complete
crawl: complete
visual: complete
review: complete
```

Pour un usage dirigeant, le mot important est le statut décisionnel, pas le
détail technique.

### 5. Commande unique de consolidation

Il faudrait une commande qui relit tous les artefacts et reconstruit un verdict
stable, indépendamment du contexte conversationnel :

```bash
shipguard finalize --results visual-tests/_results
```

Objectif : pouvoir reprendre un run interrompu sans dépendre de la mémoire de
l'agent principal.

## Ce que je transmettrais à Loïc

Le retour court :

```text
ShipGuard a bien servi sur MadeInFrance : process, crawl, visuel et review sont
verts, les artefacts sont utilisables, et l'outil a remonté un vrai risque
image bomb que les tests standards ne formalisaient pas encore complètement.
Ce risque applicatif a depuis été corrigé et verrouillé par CI.

Le point faible observé est l'orchestration audit multi-agent : une zone a rendu,
deux zones ont expiré, puis une sous-zone a été lancée. Le run reste exploitable,
mais il a dû être marqué partial.

Demande produit : borner les zones par timeout/budget, écrire un artefact
partiel obligatoire, ajouter max_agent_depth=1, et fournir un statut final
COMPLETE/PARTIAL/FAILED très lisible.

Ce n'est pas un bug bloquant, mais c'est le prochain palier pour que ShipGuard
devienne fiable en usage de décision.
```

## Limites du post-mortem

- Le run a été effectué dans un contexte conversationnel long.
- Deux agents d'audit ont été interrompus après expiration, donc l'audit code
  multi-agent n'est pas complet.
- Les findings applicatifs ont été vérifiés par lecture locale et reproduction,
  mais pas tous produits par des agents ShipGuard terminés.
- Aucun corpus Sircom réel n'a été utilisé.
- Les artefacts `visual-tests/_results/` sont locaux et ignorés par Git.

## Recommandation

Pour MadeInFrance : les findings applicatifs issus de ce run sont fermés côté
code et CI. Une relance ShipGuard complète peut être utile comme contrôle de
non-régression, mais il ne reste pas de correctif applicatif connu à faire sur
ce paquet de risques.

Pour ShipGuard : traiter la déterminisation de la lane audit avant d'ajouter de
nouvelles capacités. Le besoin prioritaire n'est pas plus d'intelligence, mais
un run qui termine proprement en complet, partiel ou échoué, avec artefacts
exploitables dans les trois cas.
