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

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
