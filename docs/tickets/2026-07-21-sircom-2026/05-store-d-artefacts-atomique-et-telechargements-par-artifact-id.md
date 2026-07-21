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

- tests unitaires du store et test API de téléchargement.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
