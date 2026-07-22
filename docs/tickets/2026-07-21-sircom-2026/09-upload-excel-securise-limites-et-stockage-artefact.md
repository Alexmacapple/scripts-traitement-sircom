# 09 - Upload Excel sécurisé, limites et stockage artefact

Statut : `ready-for-agent`

Dépend de : 05, 08.

À construire : le téléversement Excel d'un lot, sécurisé, borné par
configuration et enregistré comme artefact d'upload.

Critères d'acceptation :

- [ ] `POST /api/lots/{lot_id}/excel` accepte un fichier Excel valide.
- [ ] Les extensions et tailles invalides sont refusées avec erreurs
      structurées.
- [ ] Une archive Excel corrompue ou illisible est refusée avec erreur
      structurée.
- [ ] Le fichier est stocké sous nom interne via `ArtifactStore`.
- [ ] Le nom original n'est jamais utilisé comme chemin de stockage.
- [ ] L'upload crée ou planifie le job `diagnostic_excel`.
- [ ] Le diagnostic n'est pas exécuté dans la requête HTTP d'upload.
- [ ] Un nouvel upload Excel invalide les étapes aval prévues.
- [ ] L'UI permet de téléverser un Excel et voit le statut changer.
- [ ] Tests pour fichier valide, trop gros, extension invalide, archive corrompue
      et lot inconnu.

Hors périmètre :

- diagnostic Excel détaillé ;
- mapping ;
- CSV.

Preuve attendue :

- tests API d'upload avec fichiers temporaires.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z02-002`.

Titre ShipGuard : les uploads valident le fichier avant de vérifier le lot
ciblé.

Décision appliquée : `POST /api/lots/{lot_id}/excel` vérifie désormais
l'existence et la mutabilité du lot avant de lire et valider le fichier Excel.
Un upload vers un lot absent retourne donc `404 SIRCOM_LOT_NOT_FOUND`, et un
upload vers un lot supprimé retourne `409 SIRCOM_LOT_NOT_MUTABLE`, même si le
fichier fourni est invalide.

Preuve locale :

- suite uploads ciblée :
  `tests.test_excel_upload tests.test_image_upload`, `21 tests`, `OK` ;
- suite complète : `181 tests`, `OK`, `2 skipped`.

Limite : le précontrôle est volontairement répété dans la transaction métier
effective pour éviter une fenêtre de concurrence entre la vérification initiale
et l'écriture de l'artefact.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
