# 17 - Aperçu CSV, validation humaine et export UTF-16

Statut : `ready-for-agent`

Dépend de : 15, 16.

À construire : générer un aperçu CSV exploitable par l'utilisateur, bloquer
l'export jusqu'à validation et produire le CSV final UTF-16.

Critères d'acceptation :

- [ ] L'aperçu montre en-têtes finaux, premières lignes, cellules vides et
      alertes.
- [ ] L'aperçu montre aussi les colonnes supprimées et les lignes supprimées.
- [ ] L'aperçu correspond aux fingerprints courants.
- [ ] L'utilisateur valide l'aperçu avant export final.
- [ ] L'export est refusé si les prérequis `export testable` ne sont pas réunis
      ou si des problèmes bloquants restent ouverts.
- [ ] L'export CSV final passe le vérificateur de contrat.
- [ ] Les images manquantes ne bloquent pas l'export CSV.
- [ ] Changer mapping, tri ou Excel invalide l'aperçu et l'export.
- [ ] Le CSV final est enregistré comme artefact courant téléchargeable par
      `artifact_id`.
- [ ] Tests API/UI pour aperçu, validation et export.

Hors périmètre :

- package zip ;
- traitement images.

Preuve attendue :

- fichier CSV de test vérifié par le contrat.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z03-002`.

Titre ShipGuard : l'export CSV peut retourner un artefact final non courant ou
illisible.

Décision appliquée : `_current_preview_artifacts` vérifie désormais que
l'aperçu et le CSV final sont tous les deux `committed`, puis contrôle la
lisibilité réelle du CSV final avec `ArtifactStore.open_for_read` avant de
l'exposer comme artefact courant. Un CSV obsolète rend l'aperçu non validé ; un
fichier final manquant ou incohérent produit une erreur
`SIRCOM_CSV_ARTIFACT_UNAVAILABLE`.

Preuve locale :

- suite CSV preview ciblée : `tests.test_csv_preview`, `4 tests`, `OK` ;
- suite complète : `182 tests`, `OK`, `2 skipped`.

Limite : le contrôle de lisibilité peut marquer un artefact illisible comme
obsolète via `ArtifactStore`. La persistance durable de cette réparation dans
les endpoints de lecture reste le sujet distinct `r1-z03-003`.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
