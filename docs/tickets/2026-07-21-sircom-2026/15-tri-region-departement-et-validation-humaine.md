# 15 - Tri région/département et validation humaine

Statut : `ready-for-agent`

Dépend de : 14.

À construire : proposer le tri région puis département quand les colonnes sont
détectées, sinon conserver l'ordre Excel avec alerte non bloquante.

Critères d'acceptation :

- [ ] L'application détecte les colonnes région et département quand elles sont
      clairement identifiables.
- [ ] L'utilisateur peut confirmer le tri proposé.
- [ ] Si les colonnes ne sont pas détectées, l'ordre Excel est conservé avec
      alerte et confirmation explicite de l'utilisateur.
- [ ] Une détection ambiguë ne choisit pas automatiquement une colonne de tri.
- [ ] La décision de tri est persistée.
- [ ] Changer la décision invalide l'aperçu CSV et le package.
- [ ] Tests pour tri confirmé et repli ordre Excel.

Hors périmètre :

- export CSV final ;
- réordonnancement manuel arbitraire.

Preuve attendue :

- tests de tri et de persistance de décision.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
