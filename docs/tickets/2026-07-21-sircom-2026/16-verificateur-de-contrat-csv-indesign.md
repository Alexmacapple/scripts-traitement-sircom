# 16 - Vérificateur de contrat CSV InDesign

Statut : `ready-for-agent`

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

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z05-001`.

Titre ShipGuard : un test dépend d'un CSV local ignoré par Git.

Décision appliquée : le test de comparaison structurelle ne lit plus le CSV
2025 stocké dans `livrables-miweb-2025/`, car ce dossier est ignoré par Git. Il
utilise désormais une référence synthétique générée en mémoire avec les mêmes
propriétés de format contrôlées : UTF-16 avec BOM, séparateur virgule et fins de
ligne LF. Le test conserve l'intention : prouver que la référence 2025 sert
d'oracle de format, pas de liste normative de colonnes.

Preuve locale :

- test ciblé :
  `tests.test_csv_contract.CsvContractTest.test_structure_comparison_uses_reference_format_not_2025_header_list`,
  `OK` ;
- suite CSV contract : `tests.test_csv_contract`, `5 tests`, `OK`.

Limite : la fixture synthétique ne valide pas le contenu réel 2025 ; elle valide
le contrat de format exercé par ce test. La compatibilité métier InDesign réelle
reste couverte par les autres validations prévues au ticket.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
