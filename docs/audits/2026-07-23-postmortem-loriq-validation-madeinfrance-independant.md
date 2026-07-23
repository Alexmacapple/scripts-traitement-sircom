# Post-mortem indépendant - Validation Loriq de MadeInFrance

Date : 2026-07-23

Destinataire : Loïc

Projet validé : `madeinfrance`

SHA MadeInFrance : `15c2ef6a0ddf9d4ef7618bdb89e4a9c3706827a0`

SHA Loriq : `549dec4dd2ba62002ae0b613475b046f3bdbc2af`

## Résumé exécutif

J'ai utilisé Loriq comme outil de validation externe de MadeInFrance, sans
modifier le dépôt applicatif réel. Le résultat est bon sur le périmètre ciblé :
Loriq ne remonte aucun finding production sur clone propre, et cinq invariants
métier critiques passent en oracles locaux puis en tests pytest ciblés.

Ce n'est pas encore un cycle opérateur Loriq complet. La validation obtenue est
une validation de garde-fous techniques, pas une preuve de bout en bout
`worker -> observe -> judge -> tests -> merge`, ni une recette complète
Excel/images/package.

Verdict court : utile et exploitable pour sécuriser MadeInFrance, mais il reste
un palier d'industrialisation avant d'en faire le filet principal de validation
des changements.

## Objectif de la session

Répondre à une question simple : est-ce que Loriq peut aider à valider le code
MadeInFrance maintenant, sans attendre un nouveau développement côté Loriq ?

La réponse est oui, à condition de l'utiliser avec un clone propre et des
oracles bornés.

## Ce qui a été exécuté

### 1. Clone propre du projet

Le dépôt réel MadeInFrance contient des artefacts runtime ignorés, notamment
`.sircom2026-data/sircom.sqlite3`. Pour éviter qu'un fichier vivant casse
l'invariant read-only de Loriq, la validation a été lancée sur un clone Git
temporaire.

Commande :

```bash
git clone --local --no-hardlinks \
  /Users/alex/Claude/projets-heberges/madeinfrance \
  /private/tmp/madeinfrance-loriq-validate-15c2ef6
```

SHA vérifié :

```text
15c2ef6a0ddf9d4ef7618bdb89e4a9c3706827a0
```

### 2. Audit produit Loriq

Commande :

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python runtime/product_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-validate-15c2ef6 \
  --analysis-only
```

Résultat :

```text
status: clean - 0 finding(s), 0 blocked check(s)
harness present: false (temporary copy used: false)
audited project unchanged: yes
```

Lecture : sur sa surface déterministe actuelle, Loriq ne détecte pas de piste
production bloquante.

### 3. Oracles métier ciblés

Un script temporaire hors dépôt a exécuté cinq probes applicatives contre le
clone :

```bash
/Users/alex/Claude/projets-heberges/madeinfrance/.venv/bin/python \
  /private/tmp/madeinfrance_loriq_validation_oracles.py \
  /private/tmp/madeinfrance-loriq-validate-15c2ef6
```

Résultat : 5/5 oracles verts.

Les invariants vérifiés :

| Invariant | Résultat |
|---|---:|
| `/api/config/limits` expose `schema_version=1` et ne fuit pas les chemins internes | OK |
| Les dimensions Excel hors borne sont refusées | OK |
| Les images hors limite de pixels sont refusées | OK |
| La garde disque basse couvre `matching_images` et `package_final` | OK |
| Le CSV InDesign respecte UTF-16 BOM, virgule, LF et colonnes obligatoires | OK |

### 4. Pytest ciblé

Commande :

```bash
/Users/alex/Claude/projets-heberges/madeinfrance/.venv/bin/python -m pytest -q \
  tests/test_web_socle.py::WebSocleTest::test_config_limits_do_not_expose_internal_paths \
  tests/test_excel_diagnostic.py::ExcelDiagnosticTest::test_cell_scan_limit_does_not_trust_declared_dimensions_only \
  tests/test_image_upload.py::ImageZipInspectionPipelineTest::test_worker_blocks_images_over_dimension_limits \
  tests/test_worker.py::LocalWorkerTest::test_default_runner_blocks_heavy_jobs_when_disk_is_below_threshold \
  tests/test_csv_contract.py::CsvContractTest::test_writer_and_verifier_match_golden_bytes_and_accept_automatic_quotes
```

Résultat :

```text
5 passed in 0.40s
```

## Ce que Loriq apporte déjà

### 1. Une validation non complaisante

Loriq ne se contente pas de dire "les tests passent". Il vérifie aussi que
l'audit ne mute pas le projet audité. Ce point a immédiatement révélé un détail
utile : le dépôt réel contient un SQLite runtime ignoré qui peut bouger pendant
l'audit. Sur clone propre, l'invariant repasse vert.

### 2. Une bonne discipline de clone propre

Pour MadeInFrance, la bonne pratique devient claire :

- ne pas auditer le checkout de travail si le serveur local ou le worker peut
  toucher `.sircom2026-data` ;
- auditer un clone Git propre ;
- garder le dépôt réel comme source de vérité, mais pas comme surface d'audit
  runtime.

### 3. Un filet efficace sur les risques déjà identifiés

Les cinq oracles ciblent les risques qui comptent vraiment après le chantier A :

- fuite de chemins internes ;
- coût réel des Excels ;
- coût réel des images ;
- manque d'espace disque avant jobs lourds ;
- contrat CSV InDesign.

Ce sont des risques terrain, pas des métriques décoratives.

## Limites de cette validation

### Pas un cycle opérateur complet

La session ne prouve pas encore :

```text
worker -> observe -> judge -> tests -> merge
```

Pourquoi :

- un run opérateur complet a besoin d'un changement réel à produire ;
- le comportement utilisé pour valider les oracles était déjà présent dans
  `main` ;
- un essai suivant a échoué en phase `worker` sur un problème Codex local
  `Operation not permitted`, avant même d'atteindre observe.

Donc la validation actuelle prouve la qualité des garde-fous ciblés, pas encore
la chaîne opérateur complète.

### Pas une recette bout en bout Sircom

La session ne couvre pas encore :

```text
création lot
-> upload Excel
-> diagnostic
-> mapping
-> fusion
-> normalisation
-> CSV
-> upload zip images
-> matching
-> rapports
-> package final
```

Les briques critiques sont testées séparément, mais le workflow complet n'est
pas encore rejoué comme scénario unique.

### Pas une validation avec données réelles

Les probes utilisent des fixtures synthétiques. C'est voulu pour éviter les
données sensibles, mais cela ne remplace pas une recette avec un corpus Sircom
anonymisé ou représentatif.

## Ce qui manque pour un vrai run Loriq complet

### 1. Un harnais signé propre sur MadeInFrance courant

Le prochain essai devrait partir d'un clone propre de `15c2ef6` ou d'un SHA plus
récent, puis générer un harnais Loriq propre et confirmé.

À confirmer :

- behavior-contract ;
- oracles ;
- engine-plan ;
- operating-envelope ;
- signatures associées.

### 2. Un ticket minuscule mais réel

Loriq complet a besoin d'un diff à produire. Il faut choisir un changement utile
mais très borné, par exemple :

- ajouter un champ public non sensible à une réponse existante ;
- renforcer un message d'erreur sans toucher au comportement métier ;
- ajouter une assertion de rapport déjà dérivable ;
- corriger une petite dette documentaire reliée à une preuve de code.

Le ticket doit toucher peu de fichiers, avoir un oracle clair et éviter les gros
flux Excel/images au premier passage complet.

### 3. Un worker stable dans l'environnement local

Le worker Codex a déjà échoué localement sur :

```text
Operation not permitted
```

Avant un run complet, il faut soit :

- lancer depuis un environnement où le worker Codex fonctionne ;
- ajuster la config worker ;
- utiliser un moteur worker CLI qui ne casse pas sur l'app-server client ;
- ou créer un chemin de validation observe/judge/tests à partir d'un patch
  préparé, en assumant que ce n'est pas un cycle opérateur complet.

### 4. Un runner oracle offline-compatible

Le runner `uv run --frozen --extra test python -c` est conceptuellement bon, mais
peut échouer si la copie d'observation doit reconstruire un venv sans réseau ou
sans cache.

Pour MadeInFrance, le runner le plus fiable en local est un outil résolu sur
`PATH` qui pointe vers un venv déjà prêt, par exemple :

```yaml
oracle_runtime:
  command_prefix: [madeinfrance-project-python, -c]
```

Le pack reste portable au niveau Loriq car il ne contient pas de chemin absolu ;
le mapping de ce nom vers un venv local appartient à l'environnement de run.

### 5. Un judge réellement disponible

Le cycle complet doit passer par le judge. Il faut vérifier que le juge configuré
est disponible et stable avant de lancer une tâche longue.

À défaut, le run peut valider jusqu'à observe puis échouer plus loin pour une
raison d'infra, ce qui serait utile mais pas une preuve end-to-end.

### 6. Une commande test calibrée

Pour un premier cycle complet, mieux vaut une commande test ciblée et rapide
plutôt qu'une suite longue. Exemple :

```bash
pytest -q tests/test_web_socle.py::WebSocleTest::test_config_limits_do_not_expose_internal_paths
```

Une fois le cycle stable, élargir vers les tests chantier A puis vers la suite
complète.

## Ce qui manque pour un parcours bout en bout Excel/images/package

Il faut construire une recette synthétique unique qui pilote l'application comme
un utilisateur :

1. créer un lot ;
2. uploader un Excel multi-onglets synthétique ;
3. attendre le diagnostic ;
4. valider ou ajuster le mapping ;
5. lancer fusion et normalisation ;
6. vérifier le CSV ;
7. uploader un zip images synthétique ;
8. lancer inspection puis matching ;
9. générer rapports ;
10. générer package final ;
11. télécharger et inspecter les artefacts.

Assertions minimales :

- CSV final UTF-16 avec BOM, virgule, LF ;
- colonnes `id_dossier`, `imageid`, `@pathimg` bien positionnées ;
- dossier `export-jpg-resize/` présent dans le package ;
- images finales JPG, largeur max 350 px ;
- rapport métier présent ;
- mapping utilisé présent avec provenance ;
- manifest cohérent ;
- absences ou ambiguïtés images listées sans bloquer si elles sont non
  bloquantes.

## Recommandation opérationnelle

Court terme : garder la validation actuelle comme garde légère avant les
chantiers à risque. Elle est rapide, lisible et déjà utile.

Étape suivante : préparer un vrai run Loriq complet sur un micro-ticket choisi
exprès pour valider la chaîne opérateur, pas pour livrer une grosse feature.

Ensuite seulement : construire le scénario bout en bout Excel/images/package,
qui est un chantier de recette à part entière.

## Verdict produit pour Loriq

Loriq aide déjà à valider MadeInFrance, mais il faut l'utiliser à la bonne
échelle :

- oui pour les garde-fous critiques, les refactors risqués, les contrats publics
  et les invariants métier ;
- non pour chaque micro-changement trivial ;
- pas encore comme bouton unique de recette complète tant que le worker local,
  le runner offline et le scénario Excel/images/package ne sont pas stabilisés.

La valeur est réelle : Loriq force à dire ce qui est prouvé, ce qui ne l'est pas
et où l'infrastructure brouille le signal.
