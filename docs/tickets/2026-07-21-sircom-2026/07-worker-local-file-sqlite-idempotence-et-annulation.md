# 07 - Worker local, file SQLite, idempotence et annulation

Statut : `ready-for-agent`

Dépend de : 05, 06.

À construire : un worker local intégré qui prend des jobs persistés, applique un
lease, utilise un `run_id`, évite les doubles exécutions dangereuses et respecte
l'annulation coopérative.

Critères d'acceptation :

- [ ] Un job peut être créé, pris par un worker, marqué en cours puis terminé.
- [ ] Un lease empêche deux workers de traiter le même job simultanément.
- [ ] Un `run_id` empêche un ancien job de terminer une étape invalidée.
- [ ] Une action utilisateur répétée ne crée pas de doublon actif dangereux.
- [ ] Une demande d'annulation est persistée et prise en compte entre
      sous-étapes.
- [ ] La progression est persistée.
- [ ] Les traitements longs ne sont pas exécutés dans une requête HTTP ni via
      `BackgroundTasks` FastAPI critiques.
- [ ] Un redémarrage du worker respecte les leases, les tentatives et le
      `run_id` courant.
- [ ] Tests pour double soumission, lease expiré, annulation et erreur
      technique.

Hors périmètre :

- logique de diagnostic Excel ;
- retry aval ;
- traitements images.

Preuve attendue :

- tests worker sur SQLite temporaire.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
