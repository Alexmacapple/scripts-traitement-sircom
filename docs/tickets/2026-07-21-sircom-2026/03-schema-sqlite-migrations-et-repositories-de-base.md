# 03 - Schéma SQLite, migrations et repositories de base

Statut : `a-recadrer`

Dépend de : 01.

À construire : la base SQLite locale avec schéma versionné et repositories
minimaux pour lots, étapes, jobs, artefacts, événements et problèmes.

Critères d'acceptation :

- [ ] Le schéma crée les tables `lots`, `etapes`, `jobs`, `artefacts`,
      `evenements` et `problemes`.
- [ ] Les champs minimaux définis par la spec d'architecture sont présents.
- [ ] Les clés étrangères, index et contraintes d'unicité utiles sont créés.
- [ ] Une table ou mécanique de version de schéma empêche les migrations
      silencieuses.
- [ ] Les migrations sont idempotentes sur une base déjà initialisée.
- [ ] Les valeurs de statut critiques sont contraintes en base ou validées par
      les repositories.
- [ ] Les repositories offrent des opérations simples de création, lecture et
      mise à jour transactionnelle.
- [ ] Les tests utilisent une base SQLite temporaire.

Hors périmètre :

- logique métier complète des statuts ;
- worker ;
- UI de lots.

Preuve attendue :

- test de migration sur base vide ;
- test de contrainte d'intégrité.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
