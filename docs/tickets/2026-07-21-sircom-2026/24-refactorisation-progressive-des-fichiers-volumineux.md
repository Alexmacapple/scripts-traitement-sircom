# 24 - Refactorisation progressive des fichiers volumineux

Statut : `done`

Dépend de : aucun, peut commencer immédiatement.

Livré : réduction de la dette de maintenabilité des grands fichiers
applicatifs révélés par l'audit Loriq, sans changer le comportement utilisateur
ni refactoriser les artefacts tiers ou générés.

## État de livraison au 2026-07-23

Ticket traité comme parent et livré en tranches courtes :

- 24A : inventaire imports et contrat public de `database.py`, livré par
  `a0dfd9f docs: ajouter contrat database 24a`.
- 24B : extraction repository/database avec compatibilité imports, livré par
  `81ce0b7 refactor: extraire repositories database`.
- 24C : découpage `app.py` autour du lifespan, du worker et des routes, livré
  par `c85e9f7 refactor: decouper app web et lifecycle`.
- 24D : découpage Jinja de `index.html` avec contrat DOM/Playwright, livré par
  `5b24ba8 refactor: decouper template index`.

Limite connue : Loriq peut encore marquer l'audit `incomplete` sur des
artefacts volumineux hors cible applicative (`uv.lock`, assets DSFR, polices,
`visual-tests/*` et note longue `docs/cuisine-moi/*`). Cette limite relève du
classement des artefacts côté audit, pas d'un reste à refactoriser dans les
trois fichiers applicatifs ciblés.

Preuves principales :

- `uv run --frozen --extra test pytest -q -rs` : `221 passed, 4 skipped`.
- `env SIRCOM_RUN_PLAYWRIGHT=1 uv run --frozen --extra test pytest tests/test_lots_playwright.py -q` :
  `4 passed`.
- `uv run --frozen --extra test ruff check .` : `All checks passed!`.
- `git diff --check` : aucune sortie.

## Énoncé du problème

L'audit Loriq du 2026-07-23 ne confirme aucun bug, mais son rapport reste
`incomplete` parce que le détecteur parent atteint son cap de lecture
déterministe à 65 536 octets sur 14 fichiers.

Cette incomplétude ne doit pas déclencher un refactor global. Elle met en
évidence deux sujets distincts :

- une dette réelle sur trois grands fichiers applicatifs ;
- des fichiers volumineux normaux qui doivent rester hors refactor :
  lockfile, assets DSFR, polices et fichiers minifiés.

## Solution

Refactoriser uniquement les sources applicatives volumineuses par étapes
verticales, avec tests inchangés ou renforcés après chaque déplacement.

Ne pas toucher au comportement métier, aux contrats API, aux libellés UI, aux
assets DSFR, à `uv.lock` ni aux polices. Les déplacements doivent préserver la
CI verte à chaque commit.

## Inventaire issu de l'audit Loriq

| Fichier | Lignes | Octets | Décision |
| --- | ---: | ---: | --- |
| `sircom2026/database.py` | 2301 | 74156 | Oui, refactor progressif utile. |
| `sircom2026/templates/index.html` | 2039 | 106149 | Oui, découpage Jinja utile. |
| `sircom2026/app.py` | 1793 | 67293 | Oui, refactor progressif utile. |
| `visual-tests/_review-template.html` | 3091 | 147123 | Seulement si on maintient ce harnais. |
| `visual-tests/build-review.mjs` | 1688 | 74748 | Seulement si ça devient pénible. |
| `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` | 629 | 68622 | Scinder seulement si la doc redevient active. |
| `uv.lock` | 1043 | 223180 | Ne pas refactoriser. |
| `sircom2026/static/dsfr/1.14.4/dsfr.min.css` | 387 | 716819 | Ne pas refactoriser, asset tiers. |
| `sircom2026/static/dsfr/1.14.4/dsfr.module.min.js` | 3 | 110823 | Ne pas refactoriser, minifié. |
| `sircom2026/static/dsfr/1.14.4/dsfr.nomodule.min.js` | 3 | 274000 | Ne pas refactoriser, minifié. |
| `sircom2026/static/dsfr/1.14.4/fonts/Spectral-*.woff*` | 303-381 | 79-114 KiB | Ne pas refactoriser ; les lignes ne sont pas significatives car ce sont des binaires. |

## Décisions d'implémentation

- Commencer par les fichiers applicatifs : `database.py`, `app.py`,
  `templates/index.html`.
- Garder les refactors mécaniques petits et vérifiables.
- Préférer l'extraction vers des modules ou partials déjà cohérents avec le
  vocabulaire du projet : routes, dépendances API, repositories, rendu de
  timeline, panneaux de workflow, formulaires.
- Ne pas mélanger refactor et correction fonctionnelle.
- Ne pas renommer les clés techniques persistées, les routes publiques ou les
  libellés UI dans ce ticket.
- Ne pas déplacer `uv.lock`, les assets DSFR ni les polices.

## Découpage recommandé

1. [24A - Inventaire imports et contrat public `database.py`](24a-inventaire-imports-et-contrat-public-database.md),
   sans refactor lourd.
2. 24B - Première extraction repository/database, avec compatibilité imports.
3. 24C - Découpage `app.py` autour du lifespan, du worker et des routes, avec
   tests worker et web.
4. 24D - Découpage Jinja de `index.html`, précédé d'un test de contrat
   DOM/Playwright.

## Critères d'acceptation

- [x] Les tests existants restent verts après chaque étape de refactor.
- [x] Les routes API publiques conservent les mêmes chemins, statuts HTTP et
      formes JSON.
- [x] Les ids HTML, attributs `data-*`, rôles ARIA et libellés visibles
      couverts par les tests Playwright restent stables.
- [x] Aucun fichier DSFR, police, lockfile ou asset minifié n'est refactorisé.
- [x] Le découpage réduit la taille ou la responsabilité d'au moins un des trois
      fichiers applicatifs ciblés.
- [x] Le rapport final du ticket liste les fichiers déplacés, les imports
      publics conservés et les tests exécutés.

## Hors périmètre

- Corriger le cap de lecture de Loriq.
- Augmenter le cap global de Loriq.
- Modifier le design DSFR ou les assets tiers.
- Réécrire la couche de persistance.
- Changer le workflow métier Sircom 2026.
- Scinder la grande note `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`
  tant qu'elle ne redevient pas une source active de décision.

## Note pour Loriq

Le retour produit côté Loriq est séparé : il vaut mieux classifier les gros
fichiers par type, plutôt qu'augmenter brutalement le cap global. Les lockfiles,
fonts, assets minifiés et binaires devraient être distingués des sources texte
auditables. Une source texte couverte par reçu enfant pourrait sortir de
`incomplete`, tandis qu'un vrai fichier applicatif trop gros resterait signalé
comme dette de maintenabilité.

## Preuve attendue

- test ciblé sur la zone déplacée ;
- `uv run --frozen --extra test pytest -q` ;
- `SIRCOM_RUN_PLAYWRIGHT=1 ... tests.test_lots_playwright` si le template ou
  les routes HTML changent ;
- `git diff --check`.

## Analyse connu-inconnu

Reformulation : le ticket 24 transforme un signal de couverture Loriq en dette
de maintenabilité ciblée. Il doit réduire le risque de grands fichiers
applicatifs sans transformer l'audit incomplet en prétexte de refonte générale.

### Ancrage

- `[^]` L'audit Loriq ne confirme aucun bug et signale 14 inconnues dues au cap
  parent de lecture à 65 536 octets.
- `[^]` Trois fichiers relèvent réellement de la maintenabilité applicative :
  `database.py`, `app.py` et `templates/index.html`.
- `[^]` Les assets DSFR, polices, fichiers minifiés et `uv.lock` sont exclus du
  refactor.
- `[~]` Les preuves attendues sont les tests ciblés, la suite `pytest`, le
  Playwright complet si le HTML change, et `git diff --check`.

### Brouillard

- `[^]` Décision manquante : faut-il traiter ce ticket comme un parent de
  refactor ou comme une première tranche exécutable ? Un ticket unique couvrant
  base, app et template peut dépasser une session agent.
- `[^]` Décision manquante : quel est l'ordre le moins risqué entre
  `database.py`, `app.py` et `templates/index.html` ? L'ordre actuel est une
  recommandation, pas une contrainte.
- `[~]` Décision manquante : quelles API internes doivent rester importables
  après découpage ? Les tests protègent le comportement, pas forcément les
  imports utilisés par de futurs agents.
- `[~]` Décision manquante : quels ids, attributs `data-*`, fragments de page et
  comportements JS constituent le contrat DOM minimal avant découpage Jinja ?
- `[.]` Décision manquante : le harnais `visual-tests/*` est-il encore actif ou
  simple artefact historique ?

### Déni

- `[^]` Hypothèse masquée : un refactor peut être "mécanique". Indice : les
  trois fichiers ciblés portent des frontières d'orchestration, de persistance et
  de rendu. Impact : un déplacement apparemment neutre peut casser l'ordre de
  transaction, le lifespan FastAPI ou les hooks JS.
- `[^]` Hypothèse masquée : la suite existante suffit comme filet. Indice : le
  ticket protège les routes et les ids, mais ne nomme pas de test de contrat DOM
  exhaustif. Impact : un découpage Jinja peut rester vert tout en cassant une
  interaction peu couverte.
- `[~]` Hypothèse masquée : réduire la taille améliore forcément la
  maintenabilité. Indice : le déclencheur vient d'un cap de lecture Loriq.
  Impact : découper par nombre d'octets plutôt que par responsabilités peut
  créer plus de couplage.
- `[~]` Hypothèse masquée : `ready-for-agent` signifie lançable tel quel. Indice
  : le ticket décrit plusieurs chantiers. Impact : un agent peut tenter une
  refonte trop large au lieu d'une tranche stable.

### Abîme

- `[^]` Scénario plausible : extraction de `database.py` créant des imports
  circulaires ou des shims incohérents. Signe précurseur : tests verts mais
  nouveaux modules difficiles à importer isolément.
- `[^]` Scénario plausible : découpage de `app.py` qui change subtilement le
  démarrage, l'arrêt ou la désactivation du worker périodique. Signe précurseur :
  écart local/CI ou flake Playwright sur les jobs.
- `[~]` Scénario plausible : partials Jinja qui conservent les ids mais changent
  l'ordre DOM, le focus ou les zones ARIA. Signe précurseur : Playwright vert
  mais navigation clavier ou restauration de focus moins fiable.
- `[~]` Scénario plausible : le ticket devient une suite de prefactors sans
  bénéfice observable pour le projet. Signe précurseur : beaucoup de modules
  nouveaux, aucun test ou rapport expliquant la responsabilité retirée du fichier
  d'origine.

### Risques prioritaires

1. Transformer un ticket de maintenance en refactor monolithique.
2. Déplacer la persistance sans contrat d'import et de transaction explicite.
3. Découper le template sans verrouiller le contrat DOM utile aux tests et au JS.
4. Optimiser pour passer sous le cap Loriq plutôt que pour améliorer la
   responsabilité des modules.

### Questions

- Faut-il créer des sous-tickets `24A/24B/24C`, ou traiter ce ticket comme un
  parent dont la première passe ne touche qu'un seul fichier ?
- Quelle cible démarre le mieux : repository/database, composition FastAPI ou
  partials Jinja ?
- Quel seuil de fin compte vraiment : taille réduite, responsabilités séparées,
  imports publics stables, ou combinaison des trois ?

Verdict connu-inconnu : prêt sous conditions. Le cadrage est bon, mais
l'exécution doit être bornée en tranches indépendantes.

## Revue avocat du diable

Steel-man : le ticket fait le bon tri entre dette réelle et bruit d'audit. Il
évite de refactoriser les assets tiers, garde les tests comme preuve et formule
le problème comme maintenabilité plutôt que comme correction fonctionnelle.

Artefact le plus critique à reviewer : le ticket 24 lui-même est bien la cible,
mais le risque réel sera dans la première tranche d'implémentation. Le premier
agent devra choisir une seule surface principale, pas ouvrir les trois fichiers
simultanément.

### Préoccupations

1. Résumé : le ticket est trop large s'il est exécuté comme une seule unité.
   Sévérité : Haute. Statut : bloquante pour une implémentation monolithique.
   Cadre : pré-mortem. Description : dans trois mois, la branche de refactor
   touche persistance, app FastAPI et template, les tests passent par chance mais
   la revue devient impossible à raisonner. Conséquence : régression subtile ou
   abandon de branche après trop de diff. Recommandation : traiter le ticket 24
   comme parent ou forcer une première passe limitée à un seul fichier.

2. Résumé : le contrat public interne de `database.py` n'est pas assez nommé.
   Sévérité : Haute. Statut : à corriger avant déplacement de modules.
   Cadre : questionnement socratique. Description : le ticket dit de conserver
   les noms publics utilisés par les tests, mais pas les imports utilisés par les
   routes, services et futurs agents. Conséquence : un découpage peut casser des
   usages non couverts ou créer des shims confus. Recommandation : avant tout
   déplacement, inventorier les imports de `Database`, `Repositories` et des
   repositories, puis garder une couche de compatibilité explicite.

3. Résumé : le découpage Jinja peut casser le comportement sans changer les ids.
   Sévérité : Moyenne. Statut : à surveiller et tester. Cadre : inversion.
   Description : pour garantir une régression UI discrète, il suffirait de
   conserver les ids tout en modifiant l'ordre DOM, le focus, les libellés
   associés ou les attributs lus par `app.js`. Conséquence : l'interface reste
   visible mais devient moins fiable pour le workflow ou l'accessibilité.
   Recommandation : ajouter un test de contrat DOM minimal avant extraction des
   partials.

4. Résumé : la métrique "gros fichier" peut pousser au mauvais découpage.
   Sévérité : Moyenne. Statut : à surveiller. Cadre : cinq pourquoi inversés.
   Description : la motivation racine est la maintenabilité, pas le passage sous
   65 536 octets. Conséquence : extraction de petits modules artificiels qui
   dispersent la logique sans réduire la complexité. Recommandation : définir le
   succès par responsabilité séparée et tests lisibles, la taille n'étant qu'un
   indicateur secondaire.

5. Résumé : le worker et le lifespan sont une zone de flake déjà observée.
   Sévérité : Moyenne. Statut : à surveiller. Cadre : modes de défaillance.
   Description : `app.py` contient le montage, le démarrage et les tâches
   périodiques ; un refactor peut changer un timing sans casser les tests unitaires.
   Conséquence : retour de flakes CI ou divergence local/CI. Recommandation :
   si `app.py` est touché, relancer explicitement Playwright et les tests worker,
   pas seulement `pytest -q`.

6. Résumé : `visual-tests/*` reste ambigu.
   Sévérité : Basse. Statut : à surveiller. Cadre : chapeau bleu. Description :
   le ticket dit "seulement si on maintient ce harnais", mais aucun propriétaire
   ni critère d'activité n'est défini. Conséquence : dette documentaire qui
   revient à chaque audit sans décision. Recommandation : créer un ticket séparé
   uniquement si le harnais est réutilisé dans une prochaine passe.

Verdict avocat du diable : livrer avec modifications. Le ticket est utile, mais
il ne doit pas être consommé comme un refactor one-shot ; il doit guider des
tranches courtes, chacune avec son filet de tests ciblé.

## Frictions pour agent LLM

Ces frictions sont volontaires : elles empêchent un agent de transformer ce
ticket en grand refactor optimiste.

### Règles de conduite

- Ne choisir qu'une cible par passe : `database.py`, `app.py` ou
  `templates/index.html`.
- Avant tout déplacement, écrire la frontière visée en une phrase : ce qui sort
  du fichier, ce qui reste, et quel comportement observable prouve l'absence de
  régression.
- Faire un inventaire des imports et usages avant de créer un nouveau module.
- Préserver les imports publics existants avec une couche de compatibilité si
  les tests ou routes les utilisent.
- Ne pas modifier les routes publiques, les clés JSON, les statuts métier, les
  ids HTML, les attributs `data-*` ni les textes visibles.
- Ne jamais déplacer `uv.lock`, DSFR, polices, fichiers minifiés ou assets tiers
  dans ce ticket.
- Ne pas viser le passage sous 65 536 octets comme objectif principal. Le but
  est une responsabilité plus claire, mesurée par le diff et les tests.

### Points de blocage

- Arrêter si la tranche nécessite de toucher deux des trois grandes surfaces
  applicatives en même temps.
- Arrêter si un import circulaire apparaît et que la correction demande un
  changement d'architecture non prévu.
- Arrêter si un test Playwright casse après un découpage Jinja et que la cause
  n'est pas immédiatement reliée au déplacement.
- Arrêter si un test worker ou retry devient instable après modification de
  `app.py`.
- Arrêter si le diff mélange refactor et changement fonctionnel.
- Arrêter si le fichier extrait ne porte pas une responsabilité nommable sans
  reprendre le nom du fichier d'origine.

### Preuves minimales par cible

- `database.py` : inventaire des imports, tests repositories ou workflow
  touchés, puis suite `pytest`.
- `app.py` : tests web, worker, retry et Playwright si le lifespan ou les pages
  changent.
- `templates/index.html` : test de contrat DOM ou Playwright ciblé avant et
  après découpage.

### Sortie attendue de l'agent

Le compte rendu final doit lister :

- la cible choisie ;
- les responsabilités déplacées ;
- les imports publics conservés ;
- les tests exécutés ;
- ce qui reste volontairement non refactorisé ;
- les limites de preuve.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Audit Loriq des inconnues restantes](../../audits/2026-07-23-loriq-deep-audit-inconnues.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [AGENTS.md](../../../AGENTS.md)
