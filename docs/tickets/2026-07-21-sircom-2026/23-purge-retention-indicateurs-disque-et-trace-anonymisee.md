# 23 - Purge, rétention, indicateurs disque et trace anonymisée

Statut : `ready-for-agent`

Dépend de : 22.

À construire : la suppression immédiate et la purge planifiée des lots, avec
indicateurs disque globaux et par lot.

Critères d'acceptation :

- [ ] La rétention par défaut est 7 jours et configurable.
- [ ] Un bouton ou endpoint permet de supprimer immédiatement un lot.
- [ ] La purge efface uploads, artefacts, rapports, packages et valeurs métier.
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

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z03-004`.

Titre ShipGuard : suppression des fichiers par la purge avant durabilité de la
transaction SQLite.

Décision appliquée : la purge devient résumable en deux temps. Elle persiste
d'abord une trace `started` et le statut de lot supprimé, puis valide cette
intention avant de toucher au répertoire du lot. Si la suppression des fichiers
réussit mais que la finalisation SQL échoue ensuite, un nouvel appel reprend la
trace `started`, conserve les compteurs de fichiers et d'octets déjà mesurés,
puis termine les suppressions SQL et passe le lot au statut `purge`.

Preuve locale :

- test ciblé de panne injectée :
  `tests.test_purge.PurgeTest.test_purge_resumes_after_files_deleted_but_sql_finalization_failed`,
  `OK` ;
- suite purge : `tests.test_purge`, `4 tests`, `OK` ;
- suite API/web proche :
  `tests.test_purge tests.test_lots_api tests.test_web_socle`, `35 tests`,
  `OK`.

Limite : ce correctif couvre la cohérence locale disque/SQLite et la reprise
idempotente. Il ne change pas le hors périmètre du ticket : sauvegarde longue
durée et tableau de bord complet d'observabilité.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
- [Revue ADHD post-cadrage](revue-adhd-post-cadrage.md)
