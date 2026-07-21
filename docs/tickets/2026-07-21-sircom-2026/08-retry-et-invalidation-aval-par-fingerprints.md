# 08 - Retry et invalidation aval par fingerprints

Statut : `ready-for-agent`

Dépend de : 07.

À construire : la mécanique de relance depuis une étape échouée, avec
invalidation explicite des étapes et artefacts aval.

Critères d'acceptation :

- [ ] Une étape échouée peut être relancée si son lot n'est pas supprimé ou
      annulé.
- [ ] Le graphe de dépendances V1 est centralisé et testé.
- [ ] La relance invalide les étapes aval selon ce graphe.
- [ ] Les artefacts aval deviennent obsolètes au lieu d'être supprimés
      silencieusement.
- [ ] Les fingerprints d'input/output sont persistés et comparés.
- [ ] Les validations humaines figent un instantané des inputs validés.
- [ ] Un événement technique trace chaque invalidation.
- [ ] Tests pour nouvel Excel, changement mapping, changement tri, nouveau zip
      images et résolution d'ambiguïté image.

Hors périmètre :

- relance d'une seule image ;
- UI avancée de rollback.

Preuve attendue :

- tests d'invalidation sur plusieurs étapes.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
