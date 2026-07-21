# 13 - Fusion multi-onglets

Statut : `a-corriger`

Dépend de : 12.

À construire : produire une table à plat à partir des onglets utiles selon la
clé logique `id_dossier`.

Critères d'acceptation :

- [ ] Les lignes de sortie correspondent à l'union des `id_dossier` non vides.
- [ ] Les colonnes `id_dossier` secondaires servent à la fusion interne et ne
      sont pas répétées dans l'export.
- [ ] L'ordre des colonnes suit l'ordre des onglets puis colonnes, sauf colonnes
      spéciales.
- [ ] Les lignes sans `id_dossier` sont supprimées et comptées.
- [ ] Les colonnes entièrement vides après traitement sont supprimées et
      comptées, même si sélectionnées.
- [ ] Les absences inter-onglets restent en cellules vides.
- [ ] Tests multi-onglets avec IDs présents dans un seul onglet, IDs communs et
      lignes sans ID.

Hors périmètre :

- normalisation de contenu avancée ;
- tri ;
- CSV final.

Preuve attendue :

- tests de fusion sur Excels synthétiques.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
