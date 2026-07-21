# 18 - Upload zip images et inspection sécurisée

Statut : `ready-for-agent`

Dépend de : 05, 08.

À construire : téléverser un zip images, l'inspecter sans extraction dangereuse
et produire un bilan structuré.

Critères d'acceptation :

- [ ] Un seul zip images est accepté par lot.
- [ ] L'extension et la signature zip sont contrôlées.
- [ ] Les tailles compressée, décompressée, nombre de fichiers et taille par
      image sont contrôlées.
- [ ] Les chemins absolus, `..`, noms vides et caractères de contrôle sont
      refusés.
- [ ] Les doublons de noms après normalisation Unicode/casse sont détectés et
      signalés.
- [ ] Les images à la racine sont listées.
- [ ] Un zip avec uniquement des images en sous-dossiers est refusé en V1 avec
      message actionnable.
- [ ] Un zip sans image traitable produit une alerte non bloquante pour le CSV.
- [ ] L'inspection nettoie le répertoire temporaire du lot en cas d'échec.
- [ ] Un nouvel upload zip invalide le traitement images et le package.
- [ ] Tests pour zip valide, signature invalide, traversal, sous-dossiers,
      doublons normalisés, zip vide et zip trop gros.

Hors périmètre :

- conversion image ;
- matching images/dossiers.

Preuve attendue :

- tests de sécurité zip.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
