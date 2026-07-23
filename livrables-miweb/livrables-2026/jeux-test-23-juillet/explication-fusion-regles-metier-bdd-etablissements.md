# Explication — fusion logique BDD et Etablissements

Date : 2026-07-23.

## Statut du document

Le **jeu de test retenu** pour la suite des validations Sircom 2026 sur le
périmètre BDD + Etablissements est le fichier Excel :

```text
excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
```

Ce document est la notice associée à ce jeu de test. Il fixe :

- règles métier décrites dans ce document ;
- la transformation appliquée depuis le fichier source ;
- les exclusions volontaires ;
- les limites à ne pas confondre avec une décision de production.

Toute reprise du fichier Excel de test doit donc partir de ces règles, ou
documenter explicitement l'écart.

## Objectif

Ce document explique la transformation appliquée au fichier source
`excel-jeu-test-2026.xlsx` pour produire un fichier exploitable par
l'application Sircom 2026.

Le fichier produit est :

```text
excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx
```

Il conserve deux onglets pour tester le flux multi-onglets :

- `BDD TT + ANALYSE DGDDI` ;
- `Etablissements`.

## Principe de fusion

La transformation ne fusionne pas physiquement les deux onglets dans une seule
feuille. Elle applique une **fusion logique** : les deux onglets sont conservés,
mais ils sont ramenés au même périmètre de dossiers.

La clé de rapprochement est `Dossier ID`.

Le fichier final contient uniquement les dossiers présents à la fois :

- dans les lignes visibles de `BDD TT + ANALYSE DGDDI` ;
- dans les lignes `Champ = Dossier` de `Etablissements`.

Cela permet à l'application de tester sa fusion multi-onglets sur deux sources
propres, avec une ligne unique par dossier dans chaque onglet.

## Règles métier appliquées

### 1. BDD comme périmètre visible du test

Seules les lignes visibles de `BDD TT + ANALYSE DGDDI` sont retenues.

Raison : la demande de test précise de ne pas prendre les lignes cachées. Les
lignes masquées sont donc exclues, même si certaines peuvent exister dans
`Etablissements`.

Conséquence :

- 563 lignes visibles avec identifiant sont considérées au départ ;
- 473 lignes masquées sont exclues.

### 2. Identification dossier

Dans l'onglet BDD, la colonne source `ID` est renommée en `Dossier ID`.

Raison : l'application Sircom 2026 détecte la clé primaire dossier à partir
d'une colonne logique `Dossier ID` ou équivalente. Le renommage rend la clé
explicite et homogène avec l'onglet `Etablissements`.

### 3. Filtre Etablissements

Dans `Etablissements`, seules les lignes où `Champ = Dossier` sont retenues.

Raison : l'onglet contient deux types de lignes :

- `Champ = Dossier` : une ligne par dossier ;
- `Champ = SIRET` : une ligne complémentaire qui peut créer des doublons de
  `Dossier ID`.

Le filtre `Champ = Dossier` rend l'onglet compatible avec la règle V1 de
l'application : une ligne unique par dossier et par onglet.

Conséquence :

- 1 034 lignes `Champ = Dossier` sont indexées ;
- 1 022 lignes `Champ != Dossier` sont exclues.

### 4. Correspondance stricte sur Dossier ID

Après filtrage, seuls les dossiers présents dans les deux onglets sont
conservés.

Raison : le fichier de test doit vérifier une fusion multi-onglets sans lignes
orphelines, afin de concentrer le test sur le rapprochement BDD ↔
Etablissements.

Conséquence :

- 561 dossiers sont conservés dans chaque onglet ;
- 2 lignes visibles de BDD sont exclues car leur identifiant textuel ne trouve
  pas de correspondance dans `Etablissements` ;
- 473 lignes `Etablissements` correspondent aux lignes BDD masquées et sont
  donc exclues de ce fichier de test.

### 5. Préservation des champs sensibles

Les champs sensibles sont conservés en texte quand ils sont présents :

- `Dossier ID` ;
- `SIRET` ;
- code postal ;
- département ;
- téléphone.

Raison : ces champs peuvent contenir des zéros initiaux, des codes
administratifs ou des formats qui ne doivent pas être convertis en nombres.

### 6. Valeurs figées

Le fichier produit contient des valeurs figées.

Raison : le diagnostic Sircom 2026 refuse les formules dans les données à
importer. Les deux onglets retenus ne nécessitent pas de recalcul pour ce test.

## Ce qui est exclu

Sont exclus volontairement :

- les lignes masquées de BDD ;
- les deux identifiants textuels visibles de BDD non présents dans
  `Etablissements` ;
- les lignes `Champ = SIRET` de `Etablissements` ;
- les onglets `OFG`, `Stats`, `Avis` et `Composition du produit`.

Ces exclusions ne signifient pas que les données sont invalides métier. Elles
définissent seulement le périmètre de ce jeu de test exploitable.

## Résultat obtenu

| Onglet | Lignes de données | Colonnes | Clé dossier |
|---|---:|---:|---|
| `BDD TT + ANALYSE DGDDI` | 561 | 18 | `Dossier ID` |
| `Etablissements` | 561 | 34 | `Dossier ID` |

Dans chaque onglet :

- 561 identifiants non vides ;
- 561 identifiants uniques ;
- 0 doublon ;
- 0 identifiant vide.

## Validation applicative

Le fichier produit a été validé avec le diagnostic Sircom 2026 :

```bash
.venv/bin/python scripts-2026/diagnose_excel.py \
  "livrables-miweb-2025/livrables 2026/jeux-test-23-juillet/excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx"
```

Résultat :

```text
excel-jeu-test-2026-exploitable-bdd-etablissements.xlsx - ACCEPTABLE
sheets: 2
BDD TT + ANALYSE DGDDI: OK, 561 identifiants uniques
Etablissements: OK, 561 identifiants uniques
```

## Limites de la règle

Cette règle est adaptée au test demandé, pas à une décision définitive de
production.

Points non tranchés :

- le statut métier des 473 lignes BDD masquées ;
- le statut métier des 2 identifiants textuels visibles ;
- la règle à appliquer aux lignes `Champ = SIRET` quand elles diffèrent des
  lignes `Champ = Dossier` ;
- l'intégration éventuelle des onglets `OFG`, `Avis` et `Composition du
  produit`.

Avant production, ces points doivent être validés métier.
