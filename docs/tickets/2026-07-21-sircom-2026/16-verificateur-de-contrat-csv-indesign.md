# 16 - Vérificateur de contrat CSV InDesign

Statut : `a-corriger`

Dépend de : 14.

À construire : un vérificateur exécutable qui prouve la compatibilité du CSV
avant ou après écriture.

Critères d'acceptation :

- [ ] Le vérificateur contrôle UTF-16 avec BOM.
- [ ] Le séparateur virgule est contrôlé.
- [ ] Les fins de ligne LF sont contrôlées.
- [ ] Le contrôle est fait au niveau octets, sans normaliser implicitement les
      fins de ligne.
- [ ] Les en-têtes sont uniques et dans l'ordre attendu.
- [ ] `id_dossier`, `imageid` et `@pathimg` sont contrôlés.
- [ ] Les cellules vides sont conservées et aucune valeur `#N/A` n'est injectée.
- [ ] Les guillemets automatiques nécessaires sont acceptés sans imposer une
      liste fixe de colonnes 2025.
- [ ] Une comparaison structurelle avec la référence CSV 2025 est disponible
      comme oracle de format, pas comme liste normative de colonnes 2026.
- [ ] Tests golden file sur fixture synthétique.

Hors périmètre :

- génération UI de l'aperçu ;
- traitement images.

Preuve attendue :

- tests au niveau octets.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
