# Post-mortem Loriq x MadeInFrance - pilote opérateur E2E

Date : 2026-07-23

Destinataire : Loïc

Projet cible : `madeinfrance`

MadeInFrance courant au moment de la note : `2bc13803525bbbb252360b435572818548d6ca4b`

Loriq utilisé : `bacoco/Loriq@549dec4dd2ba62002ae0b613475b046f3bdbc2af`

## Résumé court

On a réussi un vrai passage de chaîne opérateur Loriq sur MadeInFrance :

```text
validate -> plan-gate -> worker -> observe -> static -> judge -> tests -> merge
```

Le run final `madeinfrance-e2e-pilot-8` termine en `status: done`, avec tous
les checks requis verts. C'est une validation utile de l'intégration Loriq,
des portes, de l'observer, du replay d'oracle et du merge contrôlé.

Mais ce n'est pas encore une validation production de Loriq sur MadeInFrance :
le pack était temporaire, le worker et le judge étaient des hooks factices, et
l'oracle E2E utilisait le venv local de MadeInFrance via chemin absolu. Le
résultat prouve que la mécanique opérateur tient ; il ne prouve pas encore la
qualité d'un diff produit par un vrai moteur IA ni la portabilité du pack.

## Ce qui a changé depuis les deux premiers retours

Les deux premiers retours disaient : Loriq aide déjà, les diagnostics de la PR
#93 sont bons, mais il manque encore un run complet `worker -> observe -> judge
-> tests -> merge`.

Ce troisième retour ferme cette boucle sur un pilote contrôlé : le run complet
est passé dans une copie temporaire instrumentée.

La nuance importante : on a volontairement choisi un changement inoffensif,
limité à un commentaire dans `tests/test_e2e_workflow.py`, pour tester la chaîne
Loriq elle-même sans risquer de modifier le produit.

## Mise en place du pilote

MadeInFrance n'a pas encore de pack `.hermes/control` natif. Un lancement direct
du runtime Loriq échoue donc logiquement sur un contrat de comportement vide :

```text
behavior-contract: contract is empty - classify preserve/change before bounded work
```

Pour avancer sans modifier le dépôt réel, j'ai créé une copie locale sous :

```text
/private/tmp/madeinfrance-loriq-e2e.VEWpc4/poc
```

Puis j'ai installé un pack Loriq temporaire avec :

- `behavior_id`: `preserve-madeinfrance-e2e-workflow` ;
- route : `code-hardening-route` ;
- chemin autorisé : `tests/test_e2e_workflow.py` ;
- seam : `tests/test_e2e_workflow.py::EndToEndWorkflowApiTest` ;
- contrat source : `tests/test_e2e_workflow.py:27-182` ;
- décision humaine `classify-preserve-change` résolue et signée ;
- oracles scellés obligatoires pour acceptation ;
- sandbox réseau des probes désactivée pour ce pilote Mac local.

Le dépôt MadeInFrance réel n'a pas été modifié par ce pilote.

## Résultat du run final

Run final :

```text
task: madeinfrance-e2e-pilot-8
status: done
baseline temporaire: c15ca2d0456487b09fd81807b9296c8b2347b00f
merge temporaire: 1946ca9873d3b5c6492969ab0dc4643912c27c7b
rapport: /private/tmp/madeinfrance-loriq-e2e.VEWpc4/madeinfrance-e2e-pilot-8-report.json
```

Checks du rapport :

| Check | Requis | Résultat |
|---|---:|---:|
| `validate` | oui | `success` |
| `plan-gate` | oui | `success` |
| `observe` | oui | `success` |
| `static` | non | `neutral` |
| `judge` | oui | `success` |
| `tests` | oui | `success` |

Phases passées dans le rapport :

```text
branch, clean, validate_pre, task_scope, reconcile, plan_gate, worker,
commit, observe, static, judge, tests, merge
```

Observation :

- un seul fichier changé : `tests/test_e2e_workflow.py` ;
- patch limité à un commentaire de pilote ;
- route budget respectée : maximum 1 fichier modifié, 40 lignes de patch ;
- oracle scellé `preserve-madeinfrance-e2e-workflow` passé ;
- sortie oracle : `ok` ;
- exit code : `0`.

Verdict judge :

```text
verdict: abstain
judge_engine: claude-opus
judge_model: fake
```

Raisons du judge factice :

- l'oracle E2E MadeInFrance a été rejoué sans régression ;
- le diff worker est bien limité à `tests/test_e2e_workflow.py`.

## Ce qui est prouvé

La chaîne opérateur Loriq sait accepter un changement borné sur MadeInFrance,
le faire passer par les gates, rejouer un oracle projet et merger uniquement si
les checks requis passent.

Les diagnostics de la PR #93 ont été utiles en pratique. Avant le run vert, les
échecs intermédiaires étaient lisibles :

- `network sandbox required but unavailable` ;
- `oracle-sandbox-denied` quand `uv` touchait un cache hors sandbox ;
- `probe_runtime_error` quand `uv` devait télécharger `Pillow` sans DNS.

La mécanique fail-closed a aussi fait son travail : les problèmes de contrat,
de signature, de runner et d'environnement ont bloqué au bon endroit au lieu de
laisser passer un état ambigu.

## Ce qui n'est pas encore prouvé

Le worker n'était pas un vrai modèle IA. Il s'agissait d'un hook local factice
qui ajoutait un commentaire inoffensif. Donc on n'a pas encore validé la qualité
d'un changement produit par Codex, Claude ou un autre moteur réel dans Loriq.

Le judge n'était pas un vrai juge modèle non plus. Le rapport indique
`judge_model: fake`. On a validé le câblage de la phase `judge`, pas la qualité
du jugement.

L'oracle E2E utilisait :

```text
/Users/alex/Claude/projets-heberges/madeinfrance/.venv/bin/python
```

C'est acceptable pour un pilote local, mais pas pour un pack portable. Le point
dur restant est donc le runtime Python offline-compatible dans la copie
d'observation.

Le parcours applicatif complet MadeInFrance existe maintenant en test API côté
projet, mais le pilote Loriq n'a pas rejoué un cas avec vraies données Sircom ni
un corpus lourd Excel/images.

## Questions concrètes pour Loïc

1. Quel est le chemin recommandé pour initialiser un premier pack `.hermes` sur
   un projet existant comme MadeInFrance, sans passer par une fixture de test ?

2. Pour les projets Python `uv`, quel runner oracle recommandes-tu quand
   l'observer rejoue dans une copie temporaire sans réseau : cache `uv`
   préchauffé, venv matérialisé, wrapper `PATH`, ou support dédié côté Loriq ?

3. Sur Mac local, faut-il accepter `require_network_sandbox_for_probes: false`
   pour les pilotes, ou configurer un backend sandbox attendu par Loriq ?

4. Pour le prochain run, veux-tu qu'on remplace d'abord les hooks factices par
   un vrai worker et un vrai judge, ou qu'on stabilise d'abord le pack et le
   runner oracle ?

5. Les scanners statiques manquants (`bandit`, `semgrep`) doivent-ils rester en
   `neutral` sur poste local, ou Loriq recommande-t-il une installation minimale
   pour rendre le check plus discriminant ?

## Recommandation côté MadeInFrance

Continuer à développer MadeInFrance avec la CI et les tests projet, sans
attendre Loriq pour chaque ticket.

En parallèle, industrialiser Loriq sur un petit ticket de conservation
comportementale :

- pack `.hermes` propre, versionné ou généré de façon reproductible ;
- oracle E2E portable ;
- worker réel ;
- judge réel ;
- même garde `tests/test_e2e_workflow.py` ;
- aucun changement métier tant que cette boucle n'est pas stable.

Le bon prochain objectif n'est pas de refaire tout le flux Sircom dans Loriq.
Le bon objectif est de faire passer un petit diff réel avec un vrai moteur, un
vrai judge et un oracle MadeInFrance portable. Une fois cette boucle fiable,
on pourra monter vers les changements Excel/images/package.

## Formulation courte à transmettre

Loriq a passé un cycle opérateur complet sur MadeInFrance dans un pack
temporaire : `validate`, `plan-gate`, `worker`, `observe`, `judge`, `tests` et
`merge` sont verts. La preuve est réelle côté mécanique, mais bornée : worker et
judge étaient factices, et l'oracle utilisait le venv local MadeInFrance par
chemin absolu. Le prochain verrou n'est plus "est-ce que Loriq peut piloter la
chaîne ?", mais "comment rendre le pack MadeInFrance portable avec un runner
Python offline-compatible et des moteurs réels ?".
