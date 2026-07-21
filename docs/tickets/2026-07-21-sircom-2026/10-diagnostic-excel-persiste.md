# 10 - Diagnostic Excel persisté

Statut : `a-corriger`

Dépend de : 09.

À construire : brancher le diagnostic Excel 2026 existant au pipeline, persister
le résultat et produire problèmes bloquants ou alertes.

Critères d'acceptation :

- [ ] Le diagnostic utilise la logique existante sans la déplacer gratuitement.
- [ ] `Sircom2.xlsx` est reconnu importable quand le fichier réel local est
      présent.
- [ ] `Sircom1.xlsx` est refusé quand le fichier réel local est présent.
- [ ] Les Excels synthétiques valides et refusés couvrent les règles V1.
- [ ] Un onglet vide est ignoré avec information ; un onglet non vide sans
      `id_dossier` détectable bloque.
- [ ] Les refus stricts détectent cellules fusionnées, en-têtes multi-lignes,
      colonnes masquées, lignes masquées, onglets masqués, formules, données sans
      en-tête, absence ou ambiguïté `id_dossier`, doublons `id_dossier` et
      collisions CSV.
- [ ] Les doublons d'en-têtes source deviennent alertes non bloquantes si la
      provenance permet de continuer.
- [ ] Un Excel refusé produit tous les problèmes détectables en une passe quand
      c'est techniquement possible.
- [ ] Le résultat est consultable par API et visible dans l'état du lot.

Hors périmètre :

- correction automatique de l'Excel ;
- mapping utilisateur.

Preuve attendue :

- tests unitaires et tests worker/API du diagnostic persisté.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
