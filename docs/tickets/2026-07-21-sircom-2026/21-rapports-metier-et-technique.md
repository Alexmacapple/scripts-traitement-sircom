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

## Complément rapport ShipGuard

2026-07-22 - SG-001 `r1-z03-001` :

- constat : `run_reports_job` exigeait un zip images, une inspection et un
  matching images courants, alors que le flux CSV autorise l'absence d'images ;
- correction locale : les rapports acceptent désormais l'absence totale de zip
  images, produisent un bilan images à zéro et n'enregistrent pas de source
  `matching_images` dans le rapport technique ; si un zip images a été fourni,
  les artefacts inspection et matching restent requis ;
- orchestration : `rapports` peut être auto-enchaîné après validation CSV sans
  parent `matching_images` prêt uniquement lorsqu'aucun zip images courant
  n'existe ;
- preuve : `tests.test_reports.ReportsApiTest.test_reports_are_generated_without_image_artifacts`,
  `tests.test_reports`, `tests.test_package tests.test_csv_preview
  tests.test_invalidation tests.test_worker`, puis `python -m unittest discover
  -s tests` avec 177 tests OK et 2 tests sautés ;
- limite : le comportement du package final sans images reste porté par le
  ticket 22 et n'est pas étendu par ce correctif.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
- [Revue ADHD post-cadrage](revue-adhd-post-cadrage.md)
