# Rapport Codex — analyse du fichier Excel 2026

Date d'analyse : 23 juillet 2026.

## 1. Verdict de raccordement avec GLM

Les analyses sont **raccord sur les principaux comptages**, mais pas sur toutes
les conclusions. Quatre corrections sont nécessaires avant de reprendre le
rapport ou le mail GLM comme référence :

1. Le classeur n'est pas compatible tel quel avec le diagnostic actuel :
   l'exécution réelle retourne `importable = false` et huit blocages.
2. Les deux identifiants non numériques de BDD sont atypiques, mais le fichier
   ne permet pas de conclure qu'ils sont invalides, parasites ou à supprimer.
3. Le rattachement d'OFG par SIRET n'est pas univoque pour tous les cas :
   sept lignes renvoient vers plusieurs dossiers et une ligne n'a pas de SIRET.
4. Dans `Etablissements`, 118 dossiers ont des valeurs différentes entre leur
   ligne `Dossier` et leur ligne `SIRET`. Filtrer sur `Champ = Dossier` produit
   bien une ligne par dossier, mais constitue une règle métier à valider.

Le [rapport GLM](./rapport-analyse-excel-2026.md) et son
[mail proposé](./mail-correction-proposee.md) restent utiles pour la structure
générale. Les affirmations ci-dessus doivent toutefois être corrigées.

## 2. Sources et méthode

Sources inspectées :

- [classeur source](./excel-jeu-test-2026.xlsx) ;
- [mail initial](./mail.md) ;
- [rapport GLM](./rapport-analyse-excel-2026.md) ;
- [mail GLM](./mail-correction-proposee.md) ;
- [contrat de données 2026](../../../docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md) ;
- [diagnostic Excel actuel](../../../sircom2026/excel_diagnostic.py).

Méthode :

- lecture directe de la structure OOXML du classeur, sans modification ;
- recomptage des lignes, identifiants, masquages et cardinalités ;
- comparaison ensembliste des identifiants entre onglets ;
- comparaison champ par champ des paires `Dossier` et `SIRET` ;
- exécution en lecture seule de `diagnose_workbook` dans l'environnement du
  projet.

Les valeurs métier des dossiers ne sont pas reproduites dans ce rapport.

## 3. Faits vérifiés

### BDD TT + ANALYSE DGDDI

- En-tête : ligne 40.
- Clé observée : colonne A, `ID`.
- Lignes de données avec ID non vide : 1 036.
- Identifiants uniques : 1 036 ; aucun doublon.
- Lignes visibles : 563.
- Lignes masquées contenant des données : 473.
- Identifiants composés uniquement de chiffres : 1 034.
- Identifiants textuels atypiques : 2, tous deux visibles et très incomplets.
- Les 39 lignes précédant l'en-tête sont vides et masquées.

Le terme « vrai dossier » ne peut pas être déduit du seul caractère numérique
de l'identifiant. Le statut métier des deux lignes atypiques reste à confirmer.

### Etablissements

- En-tête : ligne 1.
- Clé observée : colonne A, `Dossier ID`.
- Lignes de données : 2 056.
- Dossiers uniques : 1 034.
- `Champ = Dossier` : 1 034 lignes et 1 034 dossiers uniques.
- `Champ = SIRET` : 1 022 lignes et 1 022 dossiers uniques.
- 1 022 dossiers ont deux lignes ; 12 n'ont qu'une ligne `Dossier`.
- Parmi les 1 022 paires, 118 diffèrent sur au moins une colonne autre que
  l'identifiant et `Champ`.

Les 1 034 identifiants numériques de BDD correspondent exactement aux 1 034
identifiants des lignes `Champ = Dossier`. Les deux identifiants atypiques de
BDD n'ont pas de contrepartie dans cet onglet.

Les 473 identifiants masqués de BDD sont présents dans `Etablissements` et ont
un SIRET et une adresse non vides. Cela prouve leur présence dans le
référentiel, mais pas leur statut actif ni leur éligibilité au publipostage.

### Autres onglets

| Onglet | Lignes | Clé dossier | Cardinalité et limite |
|---|---:|---|---|
| OFG | 54 | Aucune ; SIRET en colonne B | 53 lignes avec SIRET, 50 SIRET uniques ; 46 rattachements univoques, 7 ambigus, 1 ligne sans SIRET |
| Stats | Plage jusqu'à la ligne 108 | Aucune | 16 formules et tableaux croisés ; onglet d'analyse |
| Avis | 74 | `Dossier ID` | 8 dossiers ; 7 à 11 lignes par dossier |
| Composition du produit | 2 514 | `Dossier ID` | 783 dossiers ; 1 à 43 lignes par dossier |

Aucune cellule fusionnée n'a été détectée dans les six onglets.

## 4. Blocages du diagnostic actuel

L'exécution réelle du diagnostic retourne un classeur non importable avec huit
blocages :

- `OFG` : deux plages de colonnes masquées et absence de clé dossier ;
- `Stats` : formules, en-tête détecté hors première ligne et absence de clé
  dossier ;
- `Etablissements` : identifiants dossier dupliqués avant prise en compte de
  `Champ` ;
- `Avis` : identifiants dossier dupliqués ;
- `Composition du produit` : identifiants dossier dupliqués.

Les plages de colonnes masquées d'OFG ne contiennent pas de données. Le
diagnostic les bloque néanmoins, car il contrôle le masquage structurel sans
tester leur contenu.

Il existe aussi une divergence interne à résoudre :

- le [contrat de données](../../../docs/specs/2026-07-21-contrat-donnees-csv-images-sircom-2026.md)
  classe les lignes masquées parmi les refus V1 ;
- le [code actuel](../../../sircom2026/excel_diagnostic.py) les ignore à
  l'import avec un avertissement.

Le mail métier ne doit donc pas présenter l'exclusion des lignes masquées comme
une règle définitivement acquise.

## 5. Comparaison ciblée avec le rapport GLM

| Affirmation GLM | Verdict Codex | Impact |
|---|---|---|
| Principaux comptages BDD et `Etablissements` | Confirmés | Base commune fiable |
| 1 034 dossiers numériques identiques entre BDD et `Champ = Dossier` | Confirmé | Correspondance exacte sur ce périmètre |
| Deux lignes textuelles automatiquement invalides | Non démontré | Décision métier requise |
| Fichier globalement compatible avec la chaîne 2026 | Contredit par le diagnostic réel | Le fichier est refusé tel quel |
| Tous les SIRET OFG sont rattachables à un dossier | Trop affirmatif | Sept lignes ont un rattachement multiple |
| Les lignes BDD masquées semblent actives car complètes | Présence confirmée, statut inconnu | Ne pas déduire l'éligibilité du remplissage |
| Filtrer `Etablissements` sur `Dossier` suffit | Techniquement vrai, métier non validé | 118 paires contiennent des différences |

## 6. Décisions à obtenir

1. Quel est le statut des deux identifiants atypiques de BDD ?
2. Le publipostage porte-t-il sur 561 identifiants numériques visibles, sur les
   1 034 identifiants numériques incluant les lignes masquées, ou sur les 1 036
   lignes avec ID ?
3. Quelle ligne d'`Etablissements` fait foi lorsque `Dossier` et `SIRET`
   diffèrent, éventuellement colonne par colonne ?
4. Si `Avis` ou `Composition` sont retenus, quelle règle transforme plusieurs
   lignes en une seule ligne par dossier ?
5. OFG doit-il être exclu ou disposer d'une règle de résolution des
   rattachements SIRET multiples et de la ligne sans SIRET ?
6. Quels champs et noms de colonnes sont attendus par le gabarit InDesign 2026 ?
7. Le métier peut-il fournir un classeur nettoyé, ou l'application doit-elle
   permettre d'écarter ou de transformer certains onglets avant le diagnostic ?

## 7. Conclusion

Le mail doit distinguer trois niveaux :

- **faits** : comptages, correspondances et cardinalités ci-dessus ;
- **hypothèses** : BDD comme base, filtre `Champ = Dossier`, exclusion des deux
  IDs atypiques ;
- **décisions métier** : population finale, source faisant foi et règles
  d'agrégation.

La version proposée par Codex est disponible dans
[mail-correction-proposee-codex.md](./mail-correction-proposee-codex.md).

Limites : aucune recalculation dans l'application Excel n'a été effectuée. Les
formules de `Stats` ne participent pas aux comptages présentés. Aucun CSV final
n'a été généré, car les décisions métier nécessaires restent ouvertes.
