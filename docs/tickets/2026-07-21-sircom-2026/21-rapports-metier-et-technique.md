# 21 - Rapports métier et technique

Statut : `ready-for-agent`

Dépend de : 17, 20.

À construire : générer les rapports métier et technique séparés, sans exposer de
valeurs sensibles dans les logs techniques.

Critères d'acceptation :

- [ ] Le rapport métier contient résumé du lot, entrées reçues, décisions
      utilisateur, diagnostic Excel, mapping, suppressions, alertes CSV, bilan
      images, problèmes et contenu attendu du package.
- [ ] Le rapport métier est généré sous le nom `rapport-metier.md`.
- [ ] Les sections fixes du rapport métier sont : résumé du lot, entrées,
      décisions utilisateur, diagnostic Excel, mapping, fusion et normalisation,
      CSV, images, intégrité, package et actions attendues.
- [ ] Le rapport inclut le mapping complet avec provenance.
- [ ] Le rapport inclut une vérification d'intégrité : IDs source, lignes CSV,
      lignes supprimées, images présentes, images manquantes, images ignorées.
- [ ] Le rapport technique contient durées, tailles, compteurs, codes erreur et
      traces anonymisées.
- [ ] Le rapport technique est généré sous le nom `rapport-technique.json`.
- [ ] Les logs techniques ne recopient pas les valeurs métier sensibles.
- [ ] Le format du rapport métier utilise des sections fixes lisibles par le
      Sircom.
- [ ] Des tests négatifs vérifient l'absence de valeurs métier sensibles dans le
      rapport technique et les logs.
- [ ] Tests sur contenu de rapport avec données synthétiques.

Hors périmètre :

- package zip final ;
- purge.

Preuve attendue :

- artefacts rapport générés sur lot de test.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
