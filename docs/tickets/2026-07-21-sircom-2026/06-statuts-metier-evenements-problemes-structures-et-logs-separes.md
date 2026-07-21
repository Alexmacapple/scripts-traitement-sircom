# 06 - Statuts métier, événements, problèmes structurés et logs séparés

Statut : `ready-for-agent`

Dépend de : 03, 04.

À construire : la couche d'état métier affichable, séparant étapes, événements,
problèmes et logs techniques.

Critères d'acceptation :

- [ ] Les statuts internes existent sans accents : `non_demarre`, `pret`,
      `en_cours`, `action_requise`, `bloque`, `termine`,
      `termine_avec_alertes`, `echoue`, `ignore`, `annule`.
- [ ] Les libellés UI sont en français.
- [ ] Les sévérités de problèmes sont `bloquant`, `alerte`, `information`.
- [ ] Un problème contient code, titre, cause, emplacement, action attendue et
      détails techniques dépliables.
- [ ] Les événements techniques sont persistés séparément des problèmes métier.
- [ ] L'UI détail lot affiche statuts, événements résumés et problèmes par
      niveau.
- [ ] Une étape avec alerte non bloquante ne peut pas être marquée `termine`
      sans mention `termine_avec_alertes`.
- [ ] Une validation humaine attendue met l'étape en `action_requise`.
- [ ] L'annulation est représentée au niveau lot, job et étape active.
- [ ] Tests pour transitions `termine`, `termine_avec_alertes`,
      `action_requise`, `bloque`, `echoue` et `annule`.

Hors périmètre :

- diagnostic Excel réel ;
- worker complet ;
- observabilité externe.

Preuve attendue :

- tests de transitions et rendu UI minimal des problèmes.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
