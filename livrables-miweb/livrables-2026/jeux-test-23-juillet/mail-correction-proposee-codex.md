Objet : Décisions nécessaires pour traiter le fichier Excel 2026

Bonjour,

Nous avons analysé le fichier Excel de test 2026. Sa structure ne permet pas,
dans son état actuel, de produire automatiquement un CSV avec une seule ligne
par dossier. Plusieurs règles métier doivent d'abord être confirmées.

## Faits vérifiés

Dans l'onglet `BDD TT + ANALYSE DGDDI` :

- l'en-tête se trouve ligne 40 et la colonne A contient l'identifiant ;
- 563 lignes avec un ID sont visibles et 473 sont masquées, soit 1 036 lignes ;
- 1 034 identifiants sont numériques et se retrouvent exactement dans
  `Etablissements` ;
- deux lignes visibles ont un identifiant textuel atypique et très peu
  d'informations. Leur statut doit être confirmé.

Dans l'onglet `Etablissements` :

- 2 056 lignes correspondent à 1 034 dossiers ;
- `Champ = Dossier` donne une ligne par dossier ;
- 1 022 dossiers ont également une ligne `Champ = SIRET` ;
- pour 118 dossiers, les lignes `Dossier` et `SIRET` contiennent au moins une
  information différente.

Les autres onglets demandent aussi une règle explicite :

- `Avis` contient plusieurs lignes pour chacun des 8 dossiers couverts ;
- `Composition du produit` contient une à 43 lignes pour 783 dossiers ;
- `OFG` n'a pas de clé dossier directe et certains SIRET renvoient vers
  plusieurs dossiers ;
- `Stats` est un onglet d'analyse avec des formules.

## Décisions demandées

Merci de confirmer :

1. Le publipostage doit-il porter sur les 561 identifiants numériques visibles,
   sur les 1 034 identifiants numériques incluant les lignes masquées, ou sur un
   autre périmètre ?
2. Les deux lignes à identifiant textuel doivent-elles être intégrées, exclues
   ou traitées manuellement ?
3. Quels onglets et quelles informations doivent alimenter le fichier final ?
4. Pour `Etablissements`, faut-il utiliser la ligne `Dossier`, la ligne
   `SIRET`, ou définir une règle colonne par colonne lorsqu'elles diffèrent ?
5. Si `Avis` ou `Composition du produit` sont retenus, comment leurs différentes
   lignes doivent-elles être regroupées en une seule ligne par dossier ?
6. `OFG` doit-il être exclu ou faire l'objet d'une règle complémentaire pour les
   SIRET rattachés à plusieurs dossiers ?
7. Quels champs et noms de colonnes sont attendus par le gabarit InDesign 2026 ?

Pour sécuriser le traitement, il faudrait également confirmer si un fichier
nettoyé peut être fourni avec :

- uniquement les onglets utiles ;
- une clé dossier clairement identifiée dans chaque onglet à rapprocher ;
- une seule ligne par dossier, ou une règle d'agrégation explicite ;
- aucune ligne ou colonne masquée à traiter ;
- aucune formule dans les données à importer.

Sans ces confirmations, nous n'appliquerons pas de fusion automatique afin
d'éviter la production d'un fichier incorrect.

Bonne journée,
