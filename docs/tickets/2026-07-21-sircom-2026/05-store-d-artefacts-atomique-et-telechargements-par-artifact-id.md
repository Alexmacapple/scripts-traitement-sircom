# 05 - Store d'artefacts atomique et téléchargements par `artifact_id`

Statut : `ready-for-agent`

Dépend de : 02, 03, 04.

À construire : un store disque centralisé pour uploads et artefacts générés,
référencé par SQLite et téléchargeable uniquement par identifiant d'artefact.

Critères d'acceptation :

- [ ] Les fichiers sont écrits dans un emplacement temporaire puis promus de
      façon atomique.
- [ ] Chaque artefact persisté possède type, rôle, chemin relatif, taille,
      empreinte SHA-256 et métadonnées minimales.
- [ ] Le téléchargement passe par `artifact_id` et vérifie l'appartenance au lot.
- [ ] Un artefact `pending`, `obsolete` ou supprimé n'est pas téléchargeable
      comme artefact courant.
- [ ] Un artefact absent, supprimé, obsolète ou appartenant à un autre lot
      retourne publiquement le même 404 stable ; aucun 403 ne révèle qu'il
      existe ailleurs.
- [ ] Aucun chemin absolu interne n'est exposé dans l'API.
- [ ] Les états `pending`, `committed` et `obsolete` sont testés.
- [ ] Un test simule un échec avant commit et vérifie que l'artefact n'est pas
      publié comme valide.
- [ ] Un contrôle de cohérence détecte fichier sans ligne SQLite et ligne SQLite
      sans fichier.

Hors périmètre :

- upload Excel complet ;
- purge de rétention ;
- package final.

Preuve attendue :

- tests unitaires du store et test API de téléchargement, dont le cas 404
  indiscernable.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z03-003`.

Titre ShipGuard : les réparations d'artefacts faites pendant des lectures
peuvent être perdues.

Décision appliquée : `Database.session()` commite désormais une transaction
implicite SQLite si une lecture a déclenché une réparation d'artefact, et
rollbacke cette transaction implicite en cas d'exception. Les lectures pures ne
changent pas de comportement, car aucune transaction n'est ouverte sans écriture.

Preuve locale :

- suite artefacts ciblée : `tests.test_artifacts`, `16 tests`, `OK` ;
- suite complète : `183 tests`, `OK`, `2 skipped`.

Limite : le correctif rend durables les réparations déclenchées par les
lectures locales. Il ne transforme pas toutes les lectures en transactions
`BEGIN IMMEDIATE`, afin d'éviter de bloquer inutilement les autres accès.

## Complément rapport ShipGuard - 2026-07-22 - statut lot après réparation

Finding traité : `SG-001`, origine stable `r1-z03-005`.

Titre ShipGuard : un artefact corrompu ou manquant n'entraîne pas de recalcul
du statut du lot.

Décision appliquée : la réparation d'artefact en lecture recalcule désormais le
statut du lot après avoir marqué l'artefact `obsolete` et créé le problème
métier. Un lot terminé avec un artefact devenu indisponible repasse donc en
`termine_avec_alertes` au lieu de garder un statut qui ne reflète plus l'alerte.

Preuve locale :

- `tests.test_artifacts.ArtifactDownloadApiTest.test_artifact_read_repair_recomputes_lot_status`,
  `OK` ;
- `tests.test_artifacts`, `17 tests`, `OK`.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
