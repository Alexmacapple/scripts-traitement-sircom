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

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
