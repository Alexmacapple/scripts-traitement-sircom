Objet : Questions sur la structure du fichier Excel 2026

Bonjour,

Nous avons commencé l’analyse du fichier Excel de test 2026.

Il n’est pas structuré comme celui de l’année dernière : les données sont réparties sur plusieurs onglets, avec des logiques différentes.

Avant d’avancer sur le mapping et le publipostage, nous avons besoin de confirmer quelques règles métier.

L’onglet BDD TT + ANALYSE DGDDI semble pouvoir servir de base principale :

- clé dossier identifiée en colonne A / ID ;
- en-tête détecté ligne 40 ;
- une ligne visible correspond à un dossier ;
- 563 dossiers visibles seraient importés ;
- les lignes masquées seraient ignorées, sauf consigne contraire.

L’onglet Etablissements contient aussi une clé dossier en colonne A / Dossier ID, mais il n’est pas exploitable tel quel pour une fusion automatique : certains dossiers apparaissent plusieurs fois. La colonne Champ distingue notamment des lignes Dossier et SIRET.

Si l’on retient uniquement les lignes Champ = Dossier, l’onglet Etablissements revient à une ligne par dossier, avec 1034 dossiers. Ce périmètre ne correspond donc pas exactement aux 563 dossiers visibles dans BDD.

En revanche, si les lignes masquées de BDD doivent être prises en compte, le périmètre revient à 1034 dossiers et correspond à l’onglet Etablissements filtré sur Champ = Dossier.

Nous pouvons techniquement détecter et rapprocher les onglets, mais nous ne pouvons pas choisir à votre place quelle ligne ou quelle information doit faire foi lorsqu’un même dossier apparaît plusieurs fois.

Il faut donc confirmer :

1. Le publipostage doit-il porter uniquement sur les dossiers visibles dans BDD, ou aussi sur les dossiers présents dans les lignes masquées ?
2. Quels onglets doivent alimenter le publipostage ?
3. Quelles informations précises doivent apparaître dans le fichier final ?
4. Pour Etablissements, faut-il utiliser :
   - uniquement les lignes Champ = Dossier ;
   - les lignes Champ = SIRET quand elles existent ;
   - certaines colonnes de Dossier et certaines colonnes de SIRET ;
   - ou exclure cet onglet du publipostage ?

Pour que le traitement puisse se faire sans blocage, l’idéal serait que le fichier d’entrée respecte les règles suivantes :

- un onglet principal avec une seule ligne par dossier ;
- une colonne servant de clé dossier clairement identifiable ;
- des en-têtes sur une seule ligne ;
- pas de lignes ou colonnes masquées contenant des données à traiter ;
- pas de cellules fusionnées ;
- pas de formules dans les données à importer, uniquement des valeurs ;
- pour chaque onglet secondaire, une clé dossier permettant le rapprochement avec l’onglet principal ;
- si un onglet secondaire contient plusieurs lignes par dossier, une règle métier explicite pour savoir quelle ligne ou quelles colonnes utiliser.

À ce stade, les onglets suivants ne semblent pas candidats à une fusion automatique simple :

- OFG : pas de clé dossier détectée, rattachement plutôt possible par SIRET ;
- Stats : onglet d’analyse avec formules ;
- Avis : plusieurs lignes possibles par dossier ;
- Composition du produit : plusieurs lignes possibles par dossier.

L’objectif est d’éviter une fusion automatique incorrecte et de valider une règle claire avant de produire le CSV final.

Bonne journée,
