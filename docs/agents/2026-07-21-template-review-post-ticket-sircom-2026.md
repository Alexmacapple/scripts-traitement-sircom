# Template de review post-ticket Sircom 2026

Date : 2026-07-21

## Usage

Utiliser cette checklist après chaque ticket d'implémentation avant commit ou
avant acceptation d'un agent.

Objectif : vérifier que le ticket livre son comportement observable sans
anticiper les tickets aval et sans affaiblir les invariants critiques.

## Métadonnées

- Ticket relu :
- Commit ou diff :
- Agent :
- Date :
- Verdict : `accepte` / `a-corriger` / `refuse`

## 1. Périmètre

- [ ] Le diff correspond au ticket demandé.
- [ ] Les dépendances amont du ticket sont livrées.
- [ ] Aucun fichier ou module d'un ticket aval n'est modifié sans justification
      explicite.
- [ ] Aucun module vide n'est créé pour "préparer la suite".
- [ ] Aucun stub ne renvoie un succès métier non implémenté.
- [ ] Le hors périmètre du ticket est respecté.

Pour le ticket 01, refuser si le diff introduit lots, uploads, tables métier,
worker, artefacts métier, mapping, CSV, images, package ou purge.

## 2. Contrats applicables

- [ ] Le ticket cite ou respecte les specs sources.
- [ ] Le contrat complémentaire applicable est respecté.
- [ ] Les termes critiques gardent leur sens : `run_id`, `lease_version`,
      `idempotency_key`, `ArtifactStore`, `ImageBindings`, `fingerprint`,
      `tombstone`, `purge`.
- [ ] Les chemins disque internes ne sont pas exposés par l'API.
- [ ] Les données métier sensibles ne sont pas écrites dans les logs techniques.

## 3. Invariants techniques

À cocher seulement quand le ticket est concerné.

- [ ] Idempotence testée.
- [ ] `run_id` propagé jusqu'aux écritures concernées.
- [ ] `lease_version` ou compare-and-set testé.
- [ ] Commit tardif rejeté.
- [ ] Crash avant commit simulé.
- [ ] Fichier sans ligne SQLite traité.
- [ ] Ligne SQLite sans fichier traitée.
- [ ] Hash invalide traité.
- [ ] Invalidation aval testée.
- [ ] Annulation coopérative testée.

Si le ticket n'est pas concerné, noter `non applicable` dans le compte rendu.

## 4. UI DSFR

À cocher dès qu'une page ou template est modifié.

- [ ] Pas de revendication RGAA ou DSFR complète.
- [ ] `html lang="fr"` présent pour les pages complètes.
- [ ] Lien d'évitement présent.
- [ ] `header`, `main`, `footer` structurés.
- [ ] Aucun `href="#"`.
- [ ] Labels de formulaire explicites.
- [ ] Erreurs reliées aux champs concernés.
- [ ] Actions visibles cohérentes avec le statut backend.
- [ ] Pas de duplication inutile de fragments statut/problèmes/actions si une
      macro partagée existe.
- [ ] Capture Playwright desktop/mobile prévue ou exécutée pour vrai écran
      métier.

## 5. Données et sécurité

- [ ] Aucun Excel réel ajouté.
- [ ] Aucun zip ajouté.
- [ ] Aucune image ajoutée.
- [ ] Aucun CSV ou package généré ajouté.
- [ ] Aucun log ou rapport généré ajouté.
- [ ] `.sircom2026-data/` et artefacts locaux restent hors Git.
- [ ] Les erreurs API restent structurées.
- [ ] Les téléchargements ne révèlent pas l'existence d'artefacts d'autres lots.

## 6. Tests

- [ ] Commande de test ciblée exécutée.
- [ ] Sortie ou résumé de test fourni.
- [ ] Tests couvrent au moins un cas d'échec, pas seulement le happy path.
- [ ] Tests temporaires n'écrivent pas dans le dépôt hors fixtures prévues.
- [ ] `git diff --check` exécuté.
- [ ] `git status --short --branch` vérifié.

## 7. Tensions LLM

Refuser ou renvoyer en correction si le diff contient :

- [ ] logique "au cas où" non demandée ;
- [ ] choix architectural non demandé ;
- [ ] comportement implicite non testé ;
- [ ] dépendance lourde non prévue ;
- [ ] code métier dans une route HTTP sans service testable ;
- [ ] abstraction prématurée ;
- [ ] contournement d'un contrat parce que "plus simple".

## 8. Verdict

Synthèse attendue :

```text
Verdict :
Ticket :
Périmètre :
Tests :
Risques restants :
Décision :
```

Décisions possibles :

- `accepte` : le ticket est terminé et le graphe peut avancer.
- `a-corriger` : correction bornée sans changer le cadrage.
- `refuse` : dépassement de périmètre, invariant cassé ou comportement non
  fiable.

