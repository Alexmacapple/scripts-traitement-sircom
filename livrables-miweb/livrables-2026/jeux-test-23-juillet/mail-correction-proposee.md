Objet : Questions sur la structure du fichier Excel 2026

Bonjour,

Nous avons analysé le fichier Excel de test 2026. Il n'a pas la même
structure que celui de 2025 : les données sont réparties sur six onglets,
avec des logiques différentes. Avant d'avancer sur le publipostage, nous
avons besoin de confirmer quelques règles métier.

## Ce que nous constatons

**Onglet « BDD TT + ANALYSE DGDDI »** — base de données principale :

- clé dossier en colonne A (libellée « ID »), en-tête ligne 40 ;
- une ligne = un dossier ;
- 1 036 lignes au total, dont **1 034 à identifiant numérique** et 2 à
  identifiant textuel atypique ;
- 563 lignes sont visibles, 473 sont masquées ;
- 2 lignes ne contiennent pas un identifiant mais du texte :
  « DOSSIER PAPIER » (ligne 224, dossier traité sur support papier, sans
  identifiant numérique) et « SARL VERRESATINE » (ligne 1076, ligne presque
  vide) ;
- aucun identifiant n'est en double.

**Onglet « Etablissements »** — référentiel des établissements :

- clé dossier en colonne A (libellée « Dossier ID »), en-tête ligne 1 ;
- 2 056 lignes pour 1 034 dossiers uniques ;
- une colonne « Champ » distingue les lignes « Dossier » (1 034 lignes, une
  par dossier) et les lignes « SIRET » (1 022 lignes).

**Bonne nouvelle** : les 1 034 dossiers de BDD et les 1 034 dossiers
d'Etablissements (Champ = Dossier) sont exactement les mêmes. Les deux
onglets sont parfaitement alignés. Les deux lignes texte de BDD n'ont pas de
contrepartie dans Etablissements.

Les autres onglets ne sont pas, tels quels, fusionnables en une seule ligne
par dossier :

- OFG : pas de clé dossier ; rattachement par SIRET. Les 50 SIRET se
  retrouvent tous dans Etablissements, mais 4 d'entre eux (couvrant 7 lignes
  OFG) renvoient vers plusieurs dossiers : le rattachement n'est donc pas
  unique.
- Avis : clé dossier présente, mais un dossier peut avoir plusieurs lignes.
  Couverture très faible : 8 dossiers seulement.
- Composition du produit : clé dossier présente, un dossier peut avoir
  plusieurs lignes. Couverture partielle : 783 dossiers.
- Stats : onglet de restitution avec formules et tableau croisé dynamique,
  pas une source de données.

Précision technique : aucune cellule fusionnée n'a été détectée dans le
fichier.

## Ce que nous ne pouvons pas décider à votre place

Nous pouvons rapprocher les onglets, mais nous ne pouvons pas choisir,
quand un même dossier apparaît plusieurs fois, quelle ligne ou quelle
information doit faire foi.

Questions à confirmer :

1. **Périmètre du publipostage** : faut-il traiter les 1 034 dossiers, ou
   seulement une partie ? En particulier, les 473 lignes actuellement
   masquées de BDD sont-elles à intégrer ou à exclure ? Précision : ces
   dossiers sont présents dans Etablissements avec un SIRET et une adresse,
   ce qui prouve leur présence dans le référentiel, mais pas leur éligibilité
   au publipostage. Sont-ils masqués pour une raison métier (en cours,
   rejetés, archivés) ou par simple effet de filtre ?
2. **Onglet maître** : BDD ou Etablissements doit-il servir de référence
   pour la liste finale des dossiers ? (À ce stade, les deux coïncident.)
3. **Deux lignes texte de BDD** (« DOSSIER PAPIER », « SARL VERRESATINE ») :
   erreur à exclure, ou dossier à traiter manuellement ?
4. **Contenu final** : quelles informations précises doivent figurer dans le
   fichier de publipostage, et depuis quels onglets ?
5. **Onglet Etablissements** : la colonne « Champ » indique le contexte
   source de la ligne ; le statut « siège social » est une dimension
   indépendante (colonne distincte). Pour les 1 022 dossiers ayant une ligne
   « Dossier » et une ligne « SIRET », les deux désignent le même
   établissement dans 1 003 cas. Dans 118 cas, le contenu des deux lignes
   diffère : quand elles diffèrent, quelle ligne et quelles colonnes faut-il
   retenir ?
6. **Onglets à plusieurs lignes par dossier** (Avis, Composition) : faut-il
   les intégrer au publipostage, quitte à avoir des cellules vides pour les
   dossiers non couverts (Avis ne couvre que 8 dossiers, Composition 783
   sur 1 034) ? Si oui, quelle règle choisir quand un dossier a plusieurs
   lignes ?
7. **OFG** : l'exclure, ou définir une règle de rattachement sachant que
   certains SIRET pointent vers plusieurs dossiers ?
8. **Gabarit InDesign 2026** : le publipostage doit-il respecter les noms de
   champs 2025, ou de nouveaux noms (`id_dossier`, mapping à préciser) ?

## Pour un traitement sans blocage

L'idéal serait un fichier d'entrée respectant :

- un onglet principal avec une seule ligne par dossier ;
- une colonne servant de clé dossier clairement identifiable ;
- des en-têtes sur une seule ligne ;
- pas de lignes ou colonnes masquées contenant des données à traiter ;
- pas de formules dans les données à importer, uniquement des valeurs ;
- pour chaque onglet secondaire, une clé dossier permettant le
  rapprochement ;
- si un onglet secondaire contient plusieurs lignes par dossier, une règle
  métier explicite indiquant quelle ligne ou quelles colonnes utiliser.

L'objectif est d'éviter une fusion automatique incorrecte et de valider
une règle claire avant de produire le CSV final.

Bonne journée,
