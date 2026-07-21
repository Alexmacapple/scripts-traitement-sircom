# 12 - Mapping par défaut, profils brouillon et validation humaine

Statut : `ready-for-agent`

Dépend de : 11.

À construire : proposer un mapping par défaut, charger un profil compatible en
brouillon et imposer une validation humaine avant transformation.

Critères d'acceptation :

- [ ] Sans profil, toutes les colonnes des onglets utiles sont sélectionnées par
      défaut.
- [ ] Le mapping conserve onglet source, lettre colonne, nom original, nom CSV,
      statut exporté ou supprimé et position de sortie.
- [ ] Le format du profil contient version, fingerprint structurel, onglets,
      en-têtes, lettres, types logiques confirmés et date de dernière
      utilisation.
- [ ] Une seule colonne `id_dossier` est exportée.
- [ ] `imageid` et `@pathimg` sont placés juste après `id_dossier`.
- [ ] Un profil compatible n'est jamais appliqué silencieusement ; il devient un
      brouillon à valider.
- [ ] L'utilisateur peut sauvegarder un profil à partir d'un mapping validé.
- [ ] Les incompatibilités de profil sont affichées.
- [ ] La validation est refusée si aucune colonne métier n'est sélectionnée.
- [ ] Les collisions de noms CSV après nettoyage bloquent la validation.
- [ ] Tests pour mapping par défaut, profil compatible, profil incompatible et
      collision.

Hors périmètre :

- fusion réelle ;
- export CSV.

Preuve attendue :

- tests de validation mapping et écran de validation minimal.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
