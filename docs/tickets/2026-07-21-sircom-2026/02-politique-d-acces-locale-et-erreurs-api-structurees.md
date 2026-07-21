# 02 - Politique d'accès locale et erreurs API structurées

Statut : `ready-for-agent`

Dépend de : 01.

À construire : une frontière d'autorisation explicite utilisable partout, même si
la V1 locale autorise tout, et un format d'erreur API stable.

Critères d'acceptation :

- [ ] Un `ActorContext` est injecté dans les routes protégées.
- [ ] Une `AccessPolicy` locale autorise les actions V1 sans authentification.
- [ ] L'autorisation sans authentification est valable uniquement pour un bind
      loopback (`127.0.0.1`, `localhost` ou `::1`) ; un host exposé sans auth
      produit un refus testable, que le mécanisme relève de la configuration ou
      de la politique d'accès.
- [ ] La politique expose des actions nommées pour créer, lire, modifier,
      télécharger et supprimer un lot ou artefact.
- [ ] La politique peut refuser un accès en test sans changer les routes.
- [ ] Les erreurs API suivent un schéma stable : code, message, détails
      optionnels, identifiant de corrélation si disponible.
- [ ] Les réponses d'erreur n'exposent pas de chemin disque interne.
- [ ] Les erreurs d'accès ne révèlent pas de données d'un autre lot.
- [ ] Pour un artefact absent, supprimé, obsolète ou appartenant à un autre lot,
      la réponse publique reste 404 avec le même code stable ; le motif réel
      reste uniquement dans un événement technique anonymisé.
- [ ] Tests pour accès autorisé, accès refusé, host non loopback sans auth,
      erreur structurée et indistinction publique 404.

Hors périmètre :

- authentification VPS réelle ;
- gestion d'utilisateurs ;
- sessions ou SSO.

Preuve attendue :

- tests API montrant le refus d'un accès par politique.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
