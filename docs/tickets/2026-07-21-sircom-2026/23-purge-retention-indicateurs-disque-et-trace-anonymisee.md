# 23 - Purge, rétention, indicateurs disque et trace anonymisée

Statut : `ready-for-agent`

Dépend de : 22.

À construire : la suppression immédiate et la purge planifiée des lots, avec
indicateurs disque globaux et par lot.

Critères d'acceptation :

- [ ] La rétention par défaut est 7 jours et configurable.
- [ ] Un bouton ou endpoint permet de supprimer immédiatement un lot.
- [ ] La purge supprime uploads, artefacts, rapports, packages et valeurs métier.
- [ ] Une trace technique anonymisée conserve date, statut final, durées,
      tailles, compteurs et erreurs techniques sans contenu sensible.
- [ ] L'usage disque global et par lot est visible.
- [ ] Une suppression demandée pendant un job actif provoque l'annulation
      coopérative puis la purge.
- [ ] La purge ne court pas en parallèle avec une écriture d'artefact.
- [ ] La purge est idempotente et laisse les lots purgés hors des listes par
      défaut.
- [ ] La trace anonymisée ne conserve pas de chemins utilisateurs complets, noms
      de fichiers originaux ni valeurs de cellules.
- [ ] Tests pour purge normale, purge pendant job actif et absence de fuite de
      fichier métier.

Hors périmètre :

- sauvegarde longue durée ;
- tableau de bord complet d'observabilité.

Preuve attendue :

- tests de purge sur data dir temporaire.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
