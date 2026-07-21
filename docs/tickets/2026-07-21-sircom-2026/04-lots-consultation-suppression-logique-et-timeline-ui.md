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

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
