# 14 - Normalisation contenu

Statut : `ready-for-agent`

Dépend de : 13.

À construire : normaliser les valeurs selon le contrat CSV 2026 avant aperçu et
export.

Critères d'acceptation :

- [ ] Les retours ligne dans les cellules deviennent `<br>`.
- [ ] Les espaces début/fin sont supprimés.
- [ ] Les espaces multiples sont réduits.
- [ ] Les dates valides détectées ou confirmées sortent en `dd/mm/yyyy`.
- [ ] Les dates invalides ou absentes sont signalées et sortent en `#N/A`.
- [ ] `id_dossier`, SIRET, téléphone, code postal, département et codes
      administratifs restent traités comme texte.
- [ ] Les zéros initiaux de ces champs texte sont conservés.
- [ ] Les valeurs vides deviennent `#N/A` et ne deviennent jamais `nan`, `NaT`
      ou `None`.
- [ ] Les prix, montants et pourcentages ne sont pas corrigés sans règle
      explicite.
- [ ] Tests pour chaque règle de normalisation.

Hors périmètre :

- tri ;
- encodage CSV ;
- correction métier manuelle.

Preuve attendue :

- tests unitaires de normalisation.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z04-005`.

Titre ShipGuard : les retours ligne CRLF deviennent deux balises `br` dans le
script d'optimisation 2025.

Décision appliquée : la convention `<br>` est conservée comme marqueur texte
pour le rechercher/remplacer InDesign de Victoria. Le script 2025 normalise
désormais les retours Windows `CRLF` et anciens Mac `CR` vers `LF` avant de
remplacer `LF` par `<br>`, ce qui évite de produire `<br><br>` pour un seul saut
logique.

Preuve locale :

- test dédié :
  `tests.test_scripts_2025_optimize_content`, `1 test`, `OK` ;
- suite proche :
  `tests.test_scripts_2025_optimize_content tests.test_scripts_2025_process_images tests.test_normalization`,
  `3 tests`, `OK`.

Limite : la preuve utilise un classeur synthétique 2025 ; aucun fichier
production Victoria n'a été exécuté.

## Complément rapport ShipGuard - 2026-07-22 - zéros initiaux 2025

Finding traité : `SG-001`, origine stable `r1-z04-006`.

Titre ShipGuard : le premier script Excel 2025 peut perdre les zéros initiaux.

Décision appliquée : `scripts-2025/0-si-cellule-vide-na.py` ne passe plus par
`pandas.read_excel`. Le script charge le classeur avec `openpyxl`, remplit
uniquement les cellules vides des lignes de données avec `#N/A`, puis sauvegarde
`Sircom_vide_na.xlsx`. Les valeurs non vides restent donc dans leur forme Excel
originale, notamment `id_dossier`, code postal, téléphone et SIRET textuels.

Preuve locale :

- test dédié :
  `tests.test_scripts_2025_fill_empty_na`, `1 test`, `OK` ;
- suite proche :
  `tests.test_scripts_2025_fill_empty_na tests.test_scripts_2025_optimize_content tests.test_scripts_2025_process_images tests.test_normalization`,
  `4 tests`, `OK`.

Limite : la preuve utilise un classeur synthétique 2025 ; aucun fichier
production Victoria n'a été exécuté.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
