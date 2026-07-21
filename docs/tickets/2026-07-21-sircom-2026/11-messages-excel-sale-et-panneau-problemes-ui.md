# 11 - Messages Excel sale et panneau problèmes UI

Statut : `ready-intrinseque-non-frontier`

Dépend de : 06, 10.

À construire : une expérience de diagnostic actionnable quand l'Excel est refusé
ou importable avec alertes.

Critères d'acceptation :

- [ ] Chaque problème Excel affiche titre, niveau, cause, emplacement et action
      attendue.
- [ ] Les détails techniques sont dépliables et ne copient pas de valeurs métier
      sensibles.
- [ ] Un Excel refusé bloque la transformation sans masquer les autres problèmes
      détectables.
- [ ] Les alertes non bloquantes permettent de continuer jusqu'au prochain point
      de validation.
- [ ] L'UI distingue `bloquant`, `alerte` et `information`.
- [ ] Tests de rendu ou de réponse API pour au moins trois erreurs Excel sale.

Hors périmètre :

- mapping ;
- transformation CSV.

Preuve attendue :

- test UI/API avec classeur synthétique refusé.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
