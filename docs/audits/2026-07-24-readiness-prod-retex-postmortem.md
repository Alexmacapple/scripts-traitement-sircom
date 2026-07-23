# Readiness prod, RETEX et postmortem - Sircom 2026

Date : 2026-07-24

Projet : `madeinfrance`

Commit applicatif audité et poussé :
`f29abfddc5a1b6cc6d18f482533db0aa2ef9e53b`

## Verdict

Le projet est prêt pour un passage en production pilote sur le périmètre Sircom
2026 testé : application web locale, workflow Excel réel, ZIP images réel,
package final, voie scriptée alternative, règles InDesign, CI GitHub, audit
navigateur, audit DSFR/RGAA automatisé ciblé et audit Loriq local.

Note objectivée : 19,4/20.

Je ne mets pas 20/20 absolu pour deux raisons de méthode :

- l'audit RGAA exécuté combine Axe, Playwright et contrôles DOM ciblés, mais il
  ne remplace pas une certification humaine complète des 106 critères RGAA ;
- le deep audit Loriq reste incomplet côté harnais, avec des inconnues dues aux
  plafonds de lecture et à l'absence de receipts enfants, même si aucun bug
  applicatif bloquant n'a été observé.

Décision recommandée : GO production pilote, avec surveillance des premiers lots
réels et conservation de la voie scriptée comme solution de repli.

## Grille de notation

| Axe | Pondération | Note | Preuve |
|---|---:|---:|---|
| Workflow web Excel, images, CSV, ZIP | 4 | 4 | E2E réel vert avec 561 lignes, 53 colonnes, 0 cellule vide, 10 images et ZIP final téléchargeable. |
| Contrat InDesign | 4 | 4 | CSV UTF-16, virgule, LF, `#N/A` dans les cellules vides métier, `imageid` et `@pathimg` conformes. |
| Voie scriptée 2026 | 3 | 3 | Run contrôlé vert, 561 lignes, 20 colonnes, 0 cellule vide, 392 `#N/A`, 10 JPG, tri métier OK. |
| Qualité code, tests, CI | 4 | 4 | Ruff, format, pytest complet, Playwright unittest et CI GitHub verts. |
| DSFR et accessibilité automatisée | 3 | 2,9 | Axe vert, AY11 sur 8 pages, 13 thèmes/106 critères chargés, 0 suspicion collectée, 0 signal visible ; pas de certification RGAA humaine. |
| Harnais Loriq et audit externe | 2 | 1,5 | `validate.py` vert et audit produit sans mutation ; deep audit incomplet par limites de harnais. |

Total : 19,4/20.

## Preuves exécutées

### CI GitHub

Commande de vérification :

```bash
gh run watch 30054445464 --repo Alexmacapple/scripts-traitement-sircom --exit-status
```

Résultat :

```text
Run CI (30054445464) completed with 'success'
```

### Qualité code

Commandes exécutées :

```bash
uv run --frozen --extra test ruff check .
uv run --frozen --extra test ruff format --check .
uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q
env SIRCOM_RUN_PLAYWRIGHT=1 .venv/bin/python -m unittest tests.test_lots_playwright tests.test_accessibility_axe
```

Résultats décisifs :

```text
All checks passed!
132 files already formatted
270 passed, 8 skipped, coverage 89.86%
Ran 6 tests - OK
```

### Workflow applicatif réel

Script de preuve :

```bash
uv run --frozen --extra test python /private/tmp/sircom_real_e2e_2026.py
```

Résultat décisif :

```json
{
  "csv": {
    "rows": 561,
    "columns": 53,
    "blank_cells": 0,
    "na_cells": 6419,
    "imageid_bad": 0,
    "pathimg_bad": 0
  },
  "images": {
    "count": 10,
    "bad": [],
    "max_width": 350
  },
  "package_bytes": 919730
}
```

Les statuts `termine_avec_alertes` restants correspondent aux alertes métier
attendues sur les images absentes dans le corpus réel. Elles ne bloquent pas le
package final.

### Voie scriptée 2026

Commande :

```bash
uv run --frozen --extra test python re-run-old-script-2026/run_jeu_test_2026.py --clean
```

Preuve de contrôle sur la sortie :

```text
rows: 561
columns: 20
blank_cells: 0
na_cells: 392
business_sort_inversions: 0
imageid_bad: 0
pathimg_bad: 0
images_count: 10
```

Le tri utilise la règle métier du script : région puis département, avec clé
numérique sur le préfixe départemental. Un contrôle alphabétique brut ferait
apparaître `99 - Autre` avant `987` comme inversion, mais ce n'est pas une
inversion selon la clé métier appliquée.

### DSFR, Axe et AY11/RGAA automatisé ciblé

Skill utilisé : `audit-rgaa-dsfr`, complété par les références
`dsfr-components` et par le dépôt local
`git-hors-workflow/ay11-pre-audit` pour les sondes de noms accessibles.

Dépendance ajoutée au profil de test :

```text
axe-playwright-python==0.1.7
```

Test Axe versionné :

```bash
env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test python -m unittest tests.test_accessibility_axe
```

Résultat :

```text
Ran 2 tests - OK
```

Pages couvertes par Axe :

- accueil ;
- accessibilité ;
- données personnelles ;
- plan du site ;
- accueil avec lot sélectionné ;
- workflow Excel ;
- workflow images ;
- workflow export.

Contrôle AY11 complémentaire initial :

```text
Probe accessible-name sur HTML rendu : BUTTON/CTRL/FORM/FIELDSET/LINK/WIDGET/
DIALOG/LANDMARK/TABINDEX/IFRAME/PROGRESS/METER/SELECT/RADIO
Signal initial : FORM-05 sur form#create-lot-form
Correction : aria-labelledby="create-lot-title"
Recontrôle : TOTAL_SIGNALS 0
```

Cette passe a été utile : Axe ne signalait pas ce formulaire, alors que la sonde
AY11 a détecté un nom accessible manquant sur une zone formulaire visible.

Contrôle AY11 élargi :

```text
Échantillon : 8 pages HTML rendues
RGAA local : valid=true, 13 thèmes, 106 critères, 258 tests
Profil rgaa-106 : executable=true, strict_human_executable=true
run-plan : 11 critères collectés, 95 critères pending_collection
observed_collections_count: 81
observed_targets_count: 292
collect_suspicions: 0
accessible_name_visible_non_pass: 0
semantic_visible_non_pass: 0
sensitive_form_visible_non_pass: 0
```

Revue exhaustive produite :
`docs/audits/2026-07-24-rgaa-106-criteres-tests-ay11.md`.

Thématiques explicitement sondées par AY11 :

- tableaux : critères HTML `5.3` et `5.7` sur les vues workflow ;
- liens et textes : sonde `semantic-text` sur `6.1`, `8.6`, `11.9` et `5.5` ;
- scripts, widgets et formulaires : noms accessibles, signaux formulaires
  sensibles, landmarks, boutons, liens et contrôles ;
- éléments obligatoires et structure : titres, hiérarchie de titres,
  présentation HTML statique et langue via `run-plan`.

Correction complémentaire issue de cette passe : le titre masqué
`h2#workflow-screens-title` du parcours workflow a été remplacé par un titre
visible DSFR, et les conteneurs workflow non structurants ont été rendus neutres
pour supprimer les violations Axe `heading-order`,
`landmark-complementary-is-top-level` et `landmark-unique`.

Capture navigateur AY11 :

```text
Pages : 8
axe_violations_total: 0
form_interactions_count: 1 sur la page d'accueil
produces_audit: false
produces_conformity: false
```

Limite AY11 assumée : la sonde `capture-browser --form-interactions` ne sait pas
remplir les champs fichier Playwright avec `fill()`. Les interactions
formulaires ont donc été lancées sur les pages sans champ fichier ; les uploads
Excel et ZIP restent couverts par les tests Playwright applicatifs et le E2E
réel.

Script de preuve :

```bash
uv run --frozen --extra test python /private/tmp/sircom_dsfr_rgaa_audit_2026.py
```

Résultat :

```json
{
  "totals": {
    "blocker": 0,
    "major": 0,
    "minor": 0
  },
  "pages": 8
}
```

Pages couvertes :

- accueil ;
- accessibilité ;
- données personnelles ;
- plan du site ;
- vue lot ;
- vue Excel ;
- vue images ;
- vue export final.

Contrôles automatisés couverts :

- `lang=fr`, titres de page et hiérarchie de titres ;
- liens d'évitement ;
- header, footer, navigation, breadcrumb, boutons, badges, tableaux et champs
  DSFR ;
- classes `fr-*` connues dans le CSS DSFR chargé ;
- grilles DSFR sans colonne orpheline ;
- absence d'identifiants dupliqués ;
- noms accessibles des liens et boutons ;
- labels de champs ;
- noms accessibles des formulaires, boutons, liens, widgets et landmarks via la
  sonde AY11 ;
- attributs `alt` des images ;
- navigation clavier sans focus bloqué ;
- absence de débordement horizontal racine sur mobile ;
- heuristique de contraste.

Limite assumée : `axe_playwright_python` a été ajouté au profil `test` pour
outiller la validation. Malgré Axe et AY11, ce résultat autorise une décision
produit pilotée, mais pas une déclaration officielle de conformité RGAA 100 %
sans revue humaine critère par critère.

### Shipguard navigateur

Commande Shipguard native :

```bash
node /Users/alex/.codex/plugins/cache/shipguard/shipguard/2.6.3/cli/shipguard.mjs run --profile=sircom-smoke --serve
```

Résultat :

```text
crawl: 67 pages, 0 broken assets
Status: 7 pass, 0 fail, 0 error, 0 stale, 0 skipped
Screenshots matched: 7/7
run: 0 finding(s). exit 0
```

Script de preuve :

```bash
uv run --frozen --extra test python /private/tmp/sircom_shipguard_browser_audit_2026.py
```

Résultat :

```json
{
  "summary": {
    "total": 7,
    "pass": 7,
    "fail": 0
  }
}
```

Scénarios couverts :

- accueil ;
- accessibilité ;
- données personnelles ;
- plan du site ;
- workflow Excel réel ;
- workflow images réel ;
- workflow export final réel.

Le navigateur ne remonte aucune erreur bloquante ; les captures sont générées
dans `visual-tests/_results/screenshots/`, dossier ignoré par Git.

### Loriq

Validation locale sur clone temporaire propre avec harnais `.hermes` local :

```text
runtime/validate.py: passed
problems: []
states: ["engine plan unconfirmed"]
```

Audit produit Loriq :

```text
audited_project_changed: false
summary.status: findings
finding_count: 1
finding: gap-source-surface-overflow, severity low
```

Deep audit Loriq :

```text
audited_project_changed: false
summary.status: incomplete
finding_count: 1
unknown_count: 23
```

Interprétation : Loriq est utile pour borner et documenter le chantier, mais le
deep audit n'est pas une preuve de fermeture totale. Les inconnues viennent des
limites de lecture déterministe, de lanes planifiées sans receipts enfants et
d'un plafond de surface source. Ce sont des limites de harnais à traiter avant
d'utiliser Loriq comme unique feu vert de production.

Détail du deep audit final :

```text
12 unknowns : deterministic detector read cap reached at 65536 bytes
7 unknowns : lane is planned but no host child receipt was supplied
3 unknowns : child evidence surface exceeded the audit lane cap
1 unknown : source files exceed the frozen write-surface cap
```

## Points corrigés pendant le chantier

- Règle 2026 `imageid` basée sur `Dossier ID`, sans préfixe `dossier-`.
- `@pathimg` renseigné avec racine Victoria par défaut et configurable.
- Cellules métier vides exportées en `#N/A`, conformément à la contrainte
  InDesign.
- Lignes complètement vides et lignes sans `Dossier ID` supprimées.
- Tri région puis département corrigé sur les colonnes métier, sans confusion
  avec le code postal.
- Téléchargement ZIP final vérifié avec serveur local actif.
- Voie scriptée 2026 isolée sans toucher aux scripts historiques 2025.
- Sorties de scripts déplacées dans `livrables_output_YYYY-MM-DD/`, ignorées par
  Git.
- `.DS_Store`, backups, livrables locaux, `.hermes`, `.claude`,
  `.agents/skills`, `.pdd` et artefacts visuels exclus du versionnement.
- `sircom_master_script.py` nettoyé des pictogrammes non souhaités.
- Documentation racine remise à jour avec focus 2026.
- Marqueur Loriq local ajouté dans `AGENTS.md` sans versionner le harnais local.
- Formulaire de création de lot nommé par son titre visible pour les lecteurs
  d'écran.
- Workflow rendu plus propre pour Axe et AY11 : titre de parcours visible,
  absence de landmark dupliqué et suppression d'un `aside` imbriqué.

## Ce que l'humain a bien fait

Le pilotage a été exigeant et utile. Les contraintes métier qui comptaient
vraiment ont été rappelées au bon moment : `#N/A` obligatoire pour InDesign,
tri région/département, racine `@pathimg`, absence de modification des scripts
historiques 2025, nécessité d'une alternative scriptée en plus de l'interface
web.

Les validations humaines ont aussi débloqué les bons endroits : confirmation
Loriq, clarification des chemins réels, correction de la règle sur les cellules
vides, demande de commit/push régulier, et refus de laisser des livrables ou
artefacts locaux dans Git.

Le meilleur choix de pilotage a été d'imposer un jeu de test réel commun. Sans
ce jeu de test, on aurait pu discuter longtemps de règles abstraites sans
prouver le comportement final.

## Ce que l'humain peut améliorer

Les demandes sont parfois arrivées en rafale, avec plusieurs objectifs mêlés :
prod, audit, documentation, Loriq, Git, accessibilité, scripts, score, RETEX.
Cela crée un risque de glissement du critère de fin. Pour un prochain projet,
il faut figer plus tôt une check-list de sortie avec trois colonnes :
`obligatoire`, `souhaitable`, `hors périmètre`.

Les chemins locaux ont changé plusieurs fois entre `livrables-miweb-2025`,
`livrables-miweb/livrables-2026` et chemins avec espaces. Il faut créer dès le
début un fichier de variables unique pour les sources, les images, la racine
`@pathimg`, le dossier de sortie et la date de run.

La contradiction sur les cellules vides a coûté du temps. Le bon réflexe pour
la suite est de marquer toute règle métier critique avec une phrase de contrat
testable : "dans le CSV final, aucune cellule vide exportée ; cellule métier
vide = `#N/A`".

## Ce que l'agent a bien fait

L'agent a convergé vers des preuves concrètes : tests unitaires, E2E API,
navigateur, DSFR/RGAA ciblé, sortie scriptée, CI GitHub, audits Loriq et
Shipguard. Les changements ont été poussés par lots, et les zones ignorées par
Git ont été clarifiées.

L'agent a aussi conservé la voie 2025 intacte, ce qui était important. La copie
2026 a été adaptée sans casser la référence historique.

Enfin, l'agent a fini par expliciter les limites de preuve : RGAA automatisé
versus certification humaine, Loriq local versus deep audit complet, alertes
images non bloquantes versus erreurs.

## Ce que l'agent doit améliorer

L'agent aurait dû détecter plus tôt la contradiction entre "cellules vides" et
`#N/A`. Cette règle était fondamentale pour InDesign et aurait dû être
sanctuarisée dès le premier contrat CSV.

L'agent aurait dû borner plus tôt les audits Loriq et Shipguard : ce sont des
outils utiles, mais ils ne remplacent pas les tests applicatifs réels. La bonne
formulation est : audit externe en complément, pas en substitution.

L'agent aurait dû écrire plus tôt un fichier de variables pour la voie scriptée,
au lieu de corriger progressivement les scripts. Le gain de maintenabilité est
clair maintenant.

L'agent aurait aussi dû éviter toute phrase trop définitive avant preuve. Sur ce
projet, les meilleures conclusions sont celles qui citent une commande, un SHA
et un résultat mesuré.

## Tension et collaboration

Il n'y a pas de tension relationnelle utile à signaler. Il y a eu une tension
technique saine : exigence de qualité, refus des cellules vides, volonté d'un
score élevé, demande d'audits croisés, refus de versionner les artefacts locaux.

Sur le plan opérationnel, l'humain a été satisfaisant pour l'agent : il a donné
des validations claires, a corrigé les hypothèses fausses, a accepté de traiter
les blocages Loriq, et a gardé le cap sur la production réelle plutôt que sur
une démonstration théorique.

Le point à améliorer est le séquençage : quand l'objectif change, il faut
réancrer explicitement le nouveau critère d'arrêt. Cela évite de relancer un
chantier complet à chaque message sans distinguer correction, audit, livraison
et capitalisation.

## Recommandations pour les prochains projets

1. Créer dès le départ un `jeu-test/` de référence avec Excel, ZIP images,
   résultat attendu et règles métier testables.
2. Écrire un contrat CSV court avant le code : encodage, séparateur, lignes
   supprimées, cellules vides, colonnes obligatoires, tri, imageid, `@pathimg`.
3. Créer un fichier de variables unique avant d'adapter des scripts historiques.
4. Garder deux voies dès que l'enjeu métier est fort : interface web et script
   reproductible.
5. Faire un audit Git avant le premier commit important : fichiers ignorés,
   livrables locaux, backups, données personnelles, artefacts de test.
6. Distinguer trois validations : tests projet, audit navigateur, audit
   accessibilité. Elles ne prouvent pas la même chose.
7. Pour RGAA, prévoir soit une dépendance axe intégrée au projet, soit une
   vraie passe humaine critère par critère.
8. Pour Loriq, préparer le pack et les receipts avant d'en faire un oracle de
   production.
9. Commiter par jalons courts : règle métier, implémentation, documentation,
   audit, correction, rapport final.
10. En fin de projet, conserver un rapport unique avec preuves, limites, score
    et décisions.

## Critère de sortie actuel

Le projet peut passer en production pilote si les conditions suivantes sont
acceptées :

- production sur le périmètre Sircom 2026 testé ;
- surveillance des premiers lots réels ;
- conservation de la voie scriptée comme repli ;
- pas de déclaration officielle RGAA 100 % sans audit humain complémentaire ;
- Loriq utilisé comme audit et capitalisation, pas comme unique feu vert
  bloquant tant que le deep audit reste incomplet.

Sous ces conditions, le verdict est GO.
