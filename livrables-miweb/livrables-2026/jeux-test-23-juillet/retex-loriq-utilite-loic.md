# RETEX Loriq - utilité dans le projet Sircom 2026

Date : 23 juillet 2026.

## Résultat court

Dans ce chantier, Loriq a été utile parce qu'il a empêché de partir trop vite dans une correction applicative mal bornée. Il a rendu visibles les prérequis de gouvernance, séparé les zones de travail et forcé une confirmation humaine avant de laisser avancer le chantier.

Son utilité n'a pas été de remplacer les tests de l'application. Son utilité a été de sécuriser le cadre avant les tests applicatifs.

## Pourquoi le projet en avait besoin

Le projet `madeinfrance` mélange plusieurs couches sensibles :

- des scripts historiques 2025 qui fonctionnaient déjà et servaient de référence métier ;
- une application 2026 qui doit reprendre ces règles dans un workflow plus robuste ;
- des données réelles Excel et ZIP images, où une petite erreur peut produire un CSV exploitable en apparence mais faux pour InDesign ;
- des règles métier difficiles à deviner sans preuve : tri région/département, génération `imageid`, génération `@pathimg`, matching images, package final.

Le risque principal n'était donc pas seulement de corriger un bug. Le risque était de corriger le mauvais périmètre, d'écraser une logique historique utile, ou de mélanger une optimisation technique avec une décision métier.

## Ce qui a bien marché avec Loriq

1. Refus du flou

Le premier dry-run a refusé le lancement parce que le contrat `preserve/change` était vide. Dans ce projet, ce refus était utile : il a évité de traiter une demande large comme une simple permission de modifier le code.

2. Mise en évidence des prérequis

Loriq a signalé que le dépôt n'avait pas encore de profil `.hermes`. Ce point aurait pu être interprété comme un blocage opaque. En réalité, c'était un prérequis de harnais à préparer avant un run opérateur complet.

3. Séparation des zones de travail

Loriq a distingué les zones utiles :

- `sircom2026-state` pour l'état applicatif 2026 ;
- `hardening` pour les scripts historiques 2025.

Cette séparation était importante dans ton cas, parce que les scripts 2025 servaient de référence et ne devaient pas être réécrits par opportunisme.

4. Confirmation humaine avant action bornée

Loriq a demandé une confirmation humaine avant de poursuivre. C'était pertinent parce que les changements touchaient un workflow de production de livrables : Excel, images, CSV InDesign, ZIP final.

5. Détection d'un état de harnais incohérent

Une confirmation a d'abord été refusée à cause de décalages dans les verrous de skills. Ce refus a été utile : il a empêché de valider un chantier avec un harnais dont l'état n'était pas cohérent.

6. Traçabilité de la décision

Après correction, la confirmation a été consommée et le validateur Loriq a pu passer. On a donc une trace du cadrage et de la décision, réutilisable si le chantier doit être rejoué ou expliqué.

## Preuve d'utilité dans ce cas précis

La preuve d'utilité de Loriq vient des blocages utiles qu'il a produits avant les changements applicatifs :

- il a refusé un contrat trop vague ;
- il a révélé l'absence de profil `.hermes` ;
- il a imposé une confirmation humaine ;
- il a refusé une validation tant que les verrous de skills n'étaient pas cohérents ;
- il a permis de reprendre le chantier avec des zones de travail explicites.

Ces refus ont économisé du risque. Ils ont évité une intervention large et mal qualifiée sur un projet où les anciennes règles métier devaient rester une source de comparaison.

## Ce que Loriq n'a pas remplacé

Loriq n'a pas validé à lui seul que Sircom 2026 fonctionnait. Ce n'était pas son rôle.

La preuve métier est venue ensuite de l'application :

- tests unitaires et workflows Python ;
- appels API locaux ;
- test navigateur de l'interface ;
- génération du package réel ;
- inspection du CSV final ;
- vérification du tri sur `Région du site de production du produit candidat` et `Département du site de production du produit candidat` ;
- vérification du champ `@pathimg` au format InDesign Mac.

Le bon partage des rôles est donc :

- Loriq cadre, borne et sécurise la décision ;
- les tests applicatifs prouvent le comportement métier.

## Pourquoi Loriq est utile à ce projet

Loriq est utile à `madeinfrance` parce que le projet évolue sous contrainte de continuité métier. On ne part pas d'une page blanche : on modernise une chaîne existante qui avait déjà des règles implicites dans les scripts 2025.

Dans ce contexte, Loriq aide à :

- préserver les références historiques ;
- éviter les corrections trop larges ;
- rendre explicites les décisions humaines ;
- distinguer un problème de harnais d'un problème applicatif ;
- laisser une trace exploitable pour refaire le chantier ;
- faire travailler le code et les tests dans un périmètre plus sûr.

## Règle de réutilisation

Pour les prochains changements Sircom 2026, Loriq est pertinent avant les modifications qui touchent :

- les règles métier ;
- le pipeline Excel, images, CSV ou package ;
- la compatibilité avec les scripts 2025 ;
- les décisions qui changent les livrables transmis.

Il est moins nécessaire pour une correction locale évidente, déjà couverte par un test simple.

La règle pratique à garder est :

1. utiliser Loriq pour cadrer le chantier et refuser le flou ;
2. garder les scripts 2025 comme référence quand ils expriment une règle métier ;
3. prouver le résultat avec les tests et artefacts applicatifs ;
4. noter les refus Loriq, car dans ce projet ce sont des signaux utiles, pas des pertes de temps.
