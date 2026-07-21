# 19 - Spike formats images Mac/VPS

Statut : `ready-for-agent`

Dépend de : 18.

À construire : décider et prouver le support réel des formats images sur
l'environnement local puis préparer l'écart VPS.

Critères d'acceptation :

- [ ] Les versions de Pillow et dépendances image sont documentées.
- [ ] JPG, PNG, WEBP et TIFF sont validés avec fixtures ou refusés clairement si
      l'environnement ne les supporte pas.
- [ ] HEIC est classé explicitement : supporté, refusé clairement, ou support
      conditionnel.
- [ ] EXIF orientation, transparence et profils couleur sont testés au minimum.
- [ ] Un résultat de spike documente les limites Mac/VPS, les dépendances système
      nécessaires et la décision V1.
- [ ] La décision alimente la liste de formats acceptés du traitement images.
- [ ] Aucun traitement final ne dépend d'un support HEIC implicite.

Hors périmètre :

- matching final ;
- production du package.

Preuve attendue :

- note courte dans `docs/specs/` ou section de ticket mise à jour ;
- tests ou smoke test image.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
