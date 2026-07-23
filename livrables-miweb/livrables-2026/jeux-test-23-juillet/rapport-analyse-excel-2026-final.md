# Rapport d'analyse — fichier Excel test 2026

Jeu de test Sircom du 23 juillet 2026.

- Date d'analyse : 2026-07-23.
- Fichier source : `excel-jeu-test-2026.xlsx` (dossier `livrables-miweb-2025/livrables 2026/jeux-test-23-juillet/`).
- Objectif : analyser le fichier de test 2026, vérifier les chiffres du mail initial (`mail.md`), confronter la structure aux règles métier 2026 verrouillées (`AGENTS.md`) et au contrat V1 (`docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`).
- Méthode : lecture du classeur via `openpyxl`, en lecture seule, sans modifier le fichier source ; exécution du diagnostic `diagnose_workbook` dans l'environnement du projet. Chaque fait chiffré a été recoupé par une passe de vérification indépendante. Les valeurs métier identifiables (numéros de dossiers, SIRET, raisons sociales) sont anonymisées dans ce rapport.

---

## 1. Synthèse exécutive

1. **Les chiffres du mail métier sont inexacts sur un point central.** L'onglet BDD contient **1 036 lignes** à identifiant, dont **1 034 à identifiant numérique** et **2 à identifiant textuel atypique**. Le mail confond 1 034 et 1 036 et laisse entendre une incohérence entre BDD et Etablissements : en réalité les deux onglets sont **alignés à zéro écart sur les 1 034 identifiants numériques**.
2. **Le fichier est refusé tel quel par le diagnostic V1 actuel.** Aucune cellule fusionnée, aucune formule ni colonne masquée avec données dans les quatre onglets porteurs (BDD, Etablissements, Avis, Composition) ; clé `id_dossier` identifiable dans quatre onglets sur six. Mais `diagnose_workbook` retourne `importable = false` avec huit blocages (cf. §4). C'est le vrai point de blocage opérationnel.
3. **OFG ne se rattache pas à un dossier unique.** 4 SIRET (couvrant 7 lignes OFG) pointent vers plusieurs dossiers ; 1 ligne OFG n'a pas de SIRET.
4. **Plusieurs décisions métier restent à valider** : statut des 2 identifiants atypiques, sort des 473 lignes masquées de BDD, choix de la ligne/colonnes dans Etablissements (118 dossiers ont deux lignes qui diffèrent), périmètre des onglets à faible couverture (Avis : 8 ; Composition : 783 sur 1 034).

---

## 2. Structure du fichier

Le classeur contient **6 onglets**.

| # | Onglet | Dimensions | En-tête | Clé dossier | Candidat fusion simple |
|---|---|---|---|---|---|
| 0 | BDD TT + ANALYSE DGDDI | 1 036 × 18 | ligne 40 | col A (`ID`) | Oui (1 ligne = 1 dossier) |
| 1 | OFG | 54 × 7 | ligne 40 | aucune (clé = SIRET) | Non (rattachement SIRET non univoque) |
| 2 | Stats | 108 × 9 | ligne 1 | aucune | Non (formules + TCD) |
| 3 | Etablissements | 2 056 × 34 | ligne 1 | col A (`Dossier ID`) | Oui, via filtre `Champ = Dossier` |
| 4 | Avis | 74 × 9 | ligne 1 | col A (`Dossier ID`) | Non (multi-lignes / dossier) |
| 5 | (3835348) Composition du produ | 2 514 × 6 | ligne 1 | col A (`Dossier ID`) | Non (multi-lignes / dossier) |

---

## 3. Faits vérifiés par onglet

### 3.1 BDD TT + ANALYSE DGDDI

- En-tête ligne 40 ; les 39 lignes au-dessus sont vides (et masquées).
- 1 036 lignes de données (lignes 41 à 1 076), **aucun identifiant en double**.
- **563 lignes visibles**, **473 lignes masquées** (masquage explicite, pas de filtre automatique).
- 1 034 identifiants sont numériques ; 2 sont textuels et atypiques :
  - ligne 224 : identifiant textuel libre (mention « dossier papier »), données partielles (région et département renseignés) ;
  - ligne 1 076 : identifiant textuel (une raison sociale), ligne quasi vide.
- **Prudence** : le caractère numérique ne suffit pas à qualifier les 1 034 de « vrais dossiers », ni les 2 autres d'invalides. Leur statut métier (test, anomalie, dossier papier légitime) reste à confirmer.

### 3.2 Etablissements

- En-tête ligne 1 ; 34 colonnes.
- 2 056 lignes pour **1 034 dossiers uniques**.
- Colonne `Champ` : `Dossier` = 1 034 lignes (une par dossier), `SIRET` = 1 022 lignes.
- 1 022 dossiers ont à la fois une ligne `Dossier` et une ligne `SIRET` ; 12 n'ont qu'une ligne `Dossier`.
- Filtre `Champ = Dossier` → 1 034 lignes, 1 034 uniques, aucun doublon.

### 3.3 Cohérence BDD ↔ Etablissements

- Les **1 034 identifiants numériques** de BDD sont **exactement** les 1 034 d'Etablissements (`Champ = Dossier`). Croisement : **0 écart**.
- Les 473 identifiants masqués de BDD sont tous présents dans Etablissements avec SIRET et adresse non vides. Cela **prouve leur présence** dans le référentiel, **pas leur éligibilité** au publipostage — leur statut (actif, rejeté, archivé) reste à confirmer.
- Les 2 identifiants textuels de BDD n'ont pas de contrepartie dans Etablissements.

### 3.4 OFG

- En-tête ligne 40 ; 54 lignes de données ; clé = SIRET (col B), pas d'`id_dossier`.
- 53 lignes ont un SIRET, 1 n'en a pas ; 50 SIRET uniques.
- Tous les SIRET sont présents dans Etablissements (`Champ = SIRET`), **aucun orphelin**. **Mais le rattachement n'est pas univoque** : 4 SIRET (couvrant 7 lignes OFG) renvoient vers **plusieurs dossiers** (ex. un même SIRET pointant vers 3 dossiers). OFG ne se rattache donc pas à un dossier unique sans règle métier.
- 2 colonnes masquées (H, CV) **totalement vides** (artéfact de mise en forme).

### 3.5 Avis

- 74 lignes, **8 dossiers uniques** ; multi-lignes par dossier (7 à 11 lignes). Couverture : 8 / 1 034 (0,8 %).

### 3.6 Composition du produit

- 2 514 lignes, **783 dossiers uniques** ; multi-lignes par dossier (1 à 43 lignes). Couverture : 783 / 1 034 (76 %).

### 3.7 Stats

- Onglet de restitution : 16 formules `GETPIVOTDATA` + un tableau croisé dynamique. Pas une source de données dossier.

---

## 4. Conformité au diagnostic V1 et aux règles 2026

Confrontation aux critères de la règle « refuser l'import si structure ambiguë » (`AGENTS.md` et contrat `docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md`) :

| Critère | État |
|---|---|
| Cellules fusionnées | 0 sur les 6 onglets — conforme |
| En-têtes multi-lignes | Non, mais BDD et OFG démarrent **ligne 40** (39 lignes vides masquées au-dessus) |
| Colonnes masquées avec données | Aucune (OFG : H et CV masquées mais vides) |
| Formules dans les données | 0 sur BDD, Etablissements, Avis, Composition (Stats : 16, hors périmètre) |
| Identification de `id_dossier` | OK sur BDD, Etablissements, Avis, Composition ; absent sur OFG et Stats |

**Exécution réelle du diagnostic (point bloquant).** `diagnose_workbook` retourne `importable = false` avec **huit blocages** :

- OFG : colonnes masquées (H, CV) + absence de clé dossier ;
- Stats : formules + en-tête hors ligne 1 + absence de clé dossier ;
- Etablissements : `id_dossier` dupliqués (la colonne A répète l'identifiant sur les lignes `Dossier` et `SIRET`) ;
- Avis : `id_dossier` dupliqués (multi-lignes) ;
- Composition : `id_dossier` dupliqués (multi-lignes).

Les colonnes masquées d'OFG sont vides : le blocage est structurel (le diagnostic contrôle le masquage sans tester le contenu), pas un problème de données.

Seul l'onglet BDD passerait le diagnostic, en alerte (lignes masquées + lignes vides avant en-tête), avec **563 identifiants visibles** selon le code — qui ne distingue pas, au stade du diagnostic, les identifiants numériques (561) des textuels (2).

**Contradiction interne à arbitrer.** Le code de diagnostic (`sircom2026/excel_diagnostic.py`) ignore les lignes masquées (alerte), alors que le contrat V1 les liste en motif de refus. **Cette divergence ne change pas le verdict global** : le classeur reste refusé dans tous les cas à cause des huit autres blocages. Elle ne jouerait que sur l'onglet BDD pris isolément.

**Tension de fond.** Les règles V1 (refus sur doublons d'`id_dossier`, refus sur lignes masquées) supposent un modèle « un onglet = une ligne par dossier ». Les données réelles 2026 ont des onglets légitimement multi-lignes (Etablissements, Avis, Composition) et des lignes masquées (BDD). Il faudra soit assouplir le contrat pour ces structures, soit définir des règles d'agrégation explicites.

Règles de traitement 2026 applicables :

- **Identifiants textuels** : la règle verrouillée (« lignes sans `id_dossier` ») vise les identifiants **vides**. Les 2 lignes atypiques ont un identifiant **non vide** (textuel) : la règle ne s'applique donc pas automatiquement. Leur statut (exclure, signaler, traiter manuellement) est une **décision métier**.
- **Absences à signaler** : Avis (1 026 dossiers non couverts) et Composition (251) devront sortir en cellules vides mais être **signalés**.
- **Champs sensibles en texte** : `id_dossier` et SIRET à préserver en texte (pas de conversion numérique).

---

## 5. Divergences avec le mail initial

- Le mail confond **1 034 et 1 036** : BDD = 1 036 lignes (1 034 numériques + 2 textuels). Le « 1 034 » correspond aux identifiants numériques et coïncide avec Etablissements.
- Le mail présente BDD et Etablissements comme **non cohérents** : vérification, ils sont alignés à 0 écart sur les 1 034 identifiants numériques.
- Le mail dit OFG « rattachement plutôt possible par SIRET » : le rattachement existe mais **n'est pas univoque**.
- Chiffres confirmés : 563 visibles, 473 masquées, 2 056 lignes Etablissements, 1 034 uniques — exacts.

Une version corrigée du mail est proposée dans `mail-sircom-2026-final.md` (le fichier `mail.md` n'a pas été modifié).

---

## 6. Décisions métier à valider

**Déjà tranché par le contrat fonctionnel V1** (`docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`, § Fusion multi-onglets) :

- **pas d'onglet maître imposé en V1** : le périmètre est l'**union des `id_dossier` non vides** de tous les onglets utiles ;
- les champs absents d'un onglet sortent en cellule vide (Avis et Composition ne réduisent donc pas le périmètre) ;
- par défaut, cette union donne **1 036 dossiers** (1 034 numériques + 2 textuels, lignes masquées incluses).

Questions restant à confirmer :

1. **Périmètre réel** : confirmer le périmètre par défaut (union = 1 036, dont 2 identifiants textuels et 473 lignes masquées), ou préciser des exclusions explicites (identifiants textuels ? lignes masquées ?).
2. **Deux identifiants textuels** : les exclure, les signaler, ou les traiter manuellement ? *(La règle verrouillée ne les couvre pas : elle vise les identifiants vides, et ceux-ci sont non vides.)*
3. **Statut des 473 lignes masquées** de BDD : motif métier (en cours, rejeté, archivé) ou simple effet de filtre ? Présence confirmée dans le référentiel, éligibilité à confirmer.
4. **Onglet Etablissements** : la colonne `Champ` indique le **contexte source** de la ligne ; le statut « siège social » est une **dimension indépendante** (col E). Sur les 1 022 dossiers ayant une ligne `Dossier` et une ligne `SIRET`, les deux lignes désignent le **même établissement dans 1 003 cas** (mais pas systématiquement). Pour **118 dossiers**, les deux lignes diffèrent : **99 ont le même SIRET mais d'autres champs différents, 19 ont un SIRET différent**. Quand les deux lignes diffèrent, quelle ligne et quelles colonnes faut-il retenir (éventuellement colonne par colonne) ?
5. **Onglets multi-lignes (Avis, Composition)** : intégrer (cellules vides + signalisation) ou exclure ? Règle d'agrégation quand un dossier a plusieurs lignes ?
6. **OFG** : exclure, ou définir une règle de rattachement sachant que 4 SIRET pointent vers plusieurs dossiers ?
7. **Gabarit InDesign 2026** (question ouverte du contrat fonctionnel) : nouveaux noms `id_dossier`/mapping, ou réemploi des champs 2025 ?
8. **Fichier nettoyé ou application tolérante** : demander un classeur nettoyé (onglets utiles, une ligne par dossier), ou permettre à l'application d'écarter/transformer certains onglets avant le diagnostic ?

---

## 7. Annexe — méthode reproductible

Analyse avec `openpyxl` (lecture seule, `data_only=True` puis `False` pour valeurs/formules), via `uv run --with openpyxl python <script>`. Diagnostic via `diagnose_workbook` du module `sircom2026.excel_diagnostic`.

Logique des vérifications :

- Comptage lignes/colonnes masquées : `ws.row_dimensions[r].hidden` / `ws.column_dimensions[letter].hidden`.
- Détection des formules : cellules dont la valeur (`data_only=False`) commence par `=`.
- Cellules fusionnées : `ws.merged_cells.ranges`.
- Clé dossier : colonne A de chaque onglet, en distinguant valeurs numériques et textuelles pour BDD.
- Croisement BDD ↔ Etablissements : comparaison ensembliste des identifiants (chaînes) entre identifiants numériques de BDD et Etablissements filtré sur `Champ = Dossier`.
- Rattachement OFG : jointure `OFG.SIRET` → `Etablissements(Champ = SIRET).Dossier ID` → `BDD.ID`, en comptant le nombre de `Dossier ID` distincts par SIRET (détection des rattachements multiples).
- Écarts Dossier/SIRET : pour les 1 022 dossiers ayant les deux lignes, comparaison colonne par colonne (hors `Dossier ID` et `Champ`) → 118 différences, décomposées en 99 (même SIRET, autres champs) et 19 (SIRET différent).

Limites :

- Lecture `data_only=True` : repose sur les valeurs calculées stockées par Excel. Aucune cellule vide suspecte observée sur les clés, mais une relecture sur les colonnes de texte libre reste possible.
- L'onglet Stats n'a pas été audité au-delà de la détection des formules et du TCD.
- Aucune recalculation dans l'application Excel n'a été effectuée ; les formules de Stats ne participent pas aux comptages. Aucun CSV final n'a été généré, car les décisions métier nécessaires restent ouvertes.
