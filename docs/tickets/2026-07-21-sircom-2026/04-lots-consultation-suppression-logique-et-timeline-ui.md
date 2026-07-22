# 04 - Lots, consultation, suppression logique et timeline UI

Statut : `ready-for-agent`

Dépend de : 02, 03.

À construire : le parcours utilisateur de création et consultation d'un lot,
avec suppression logique et timeline d'étapes visible.

Critères d'acceptation :

- [ ] `POST /api/lots` crée un lot avec étapes V1 initialisées.
- [ ] `GET /api/lots` liste les lots avec pagination simple sans charger les
      artefacts lourds.
- [ ] `GET /api/lots/{lot_id}` retourne statut global, étapes et compteurs
      simples.
- [ ] `DELETE /api/lots/{lot_id}` marque le lot supprimé sans encore purger les
      fichiers métier.
- [ ] Les lots supprimés logiquement sont exclus de la liste par défaut.
- [ ] L'UI permet de créer un lot, le sélectionner et voir sa timeline.
- [ ] La timeline affiche les libellés français des étapes V1.
- [ ] Les routes vérifient la politique d'accès.
- [ ] Tests API pour création, consultation, lot inconnu et suppression logique.

Hors périmètre :

- purge physique ;
- upload Excel ;
- worker.

Preuve attendue :

- tests `TestClient` et vue UI minimale fonctionnelle.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z01-001`.

Titre ShipGuard : suppression de lot déclenchée en un clic sans confirmation.

Décision appliquée : le bouton de suppression expose désormais le titre du lot
avec `data-lot-title`, et `sircom2026/static/app.js` appelle une confirmation
navigateur avant toute requête `DELETE /api/lots/{lot_id}`. Si l'utilisateur
annule, aucun état occupé n'est appliqué au bouton et aucune suppression n'est
déclenchée.

Preuve locale :

- suite lots `TestClient` : `tests.test_lots_api`, `15 tests`, `OK` ;
- parcours navigateur explicite :
  `SIRCOM_RUN_PLAYWRIGHT=1 tests.test_lots_playwright`, `2 tests`, `OK` ;
- suite complète : `179 tests`, `OK`, `2 skipped`.

Limite : la confirmation utilise le dialogue natif `window.confirm`, sans
modale DSFR dédiée. Ce choix garde la correction minimale et fournit
l'annulation native du navigateur.

## Complément rapport ShipGuard - 2026-07-22 - tests UI lots

Findings traités : `SG-001`, origines stables `r1-z01-002` et `r1-z05-004`.

Titres ShipGuard : le test visuel d'accueil ne vérifie pas explicitement le
bouton Créer le lot ; le test Playwright choisit un port libre puis le relâche
avant Uvicorn.

Décision appliquée : le manifeste visuel d'accueil vérifie désormais le libellé
`Créer le lot`. Le serveur Playwright conserve une socket TCP déjà liée et la
passe à Uvicorn, ce qui évite de libérer le port entre la découverte et le
démarrage du serveur.

Preuve locale :

- `node visual-tests/build-review.mjs` : `2 pass`, `0 fail`, `0 error` ;
- `SIRCOM_RUN_PLAYWRIGHT=1 tests.test_lots_playwright`, `2 tests`, `OK`.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
