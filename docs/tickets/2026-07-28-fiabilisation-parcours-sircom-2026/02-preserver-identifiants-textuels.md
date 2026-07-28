# 02 - Préserver les identifiants textuels

Statut : `blocked`

Dépend de : 05. Commencer seulement quand 05 est `done`.

À construire : tout identifiant reconnu par le web ou la voie scriptée suit le
même contrat de type et de canonicalisation, sans filtrage silencieux ni perte
des zéros initiaux.

## Contexte

Une modification locale préexistante accepte l'en-tête `ID`, mais élimine
ensuite toute ligne dont la valeur ne correspond pas uniquement à des chiffres.
Le script termine avec succès et peut annoncer que l'intégrité est confirmée.

Le contrat Sircom ne définit pas `Dossier ID` comme un entier. La normalisation
nécessaire à `imageid` ne justifie pas la suppression d'un identifiant métier
non vide.

Le web convertit actuellement des valeurs de cellule en chaînes et peut
atteindre l'aperçu CSV sans exécuter le matching images. Le contrat de type et
le contrôle de collision `imageid` doivent donc intervenir dans le parcours
données, pas dépendre de la présence d'un ZIP.

## Critères d'acceptation

- [ ] Dans les deux parcours, les en-têtes acceptés comme identifiant appliquent
      tous la même règle métier.
- [ ] Seules les lignes dont l'identifiant est réellement vide sont supprimées.
- [ ] La clé est une chaîne Unicode opaque : casse, ponctuation, séparateurs et
      espaces internes sont préservés sans allowlist.
- [ ] Seuls les espaces périphériques sont retirés. Une valeur vide après ce
      retrait est absente ; deux valeurs alors identiques sont des doublons.
- [ ] `id_dossier` exporte exactement cette clé canonique ; aucune valeur brute
      d'un onglet n'est retenue comme variante de sortie.
- [ ] Une cellule textuelle conserve ses zéros initiaux.
- [ ] Une cellule numérique est acceptée seulement si elle n'est pas booléenne,
      est finie, entière, strictement comprise entre `-10^15` et `10^15`, et
      porte le format `General` ou `0`. Elle devient une chaîne décimale ASCII
      sans séparateur ni `.0`.
- [ ] Booléen, date ou heure, erreur, formule, nombre non entier ou non fini,
      nombre hors plage et autre format numérique sont refusés avec
      `SIRCOM_ID_REQUIRES_TEXT`, l'onglet et la cellule, sans recopier la
      valeur.
- [ ] Le bilan de l'extraction distingue lignes vides, lignes sans identifiant
      et erreurs de structure ; il ne confirme pas l'intégrité après une perte
      non justifiée.
- [ ] Le vérificateur final applique la même définition de l'identifiant que
      l'extracteur.
- [ ] Les tests couvrent au minimum une valeur numérique, une valeur
      alphanumérique, ponctuation et séparateurs, une valeur textuelle avec zéro
      initial, une valeur numérique formatée avec zéros, une valeur entourée
      d'espaces et une valeur vide.
- [ ] Un test de non-régression prouve que `imageid` reste déterministe pour les
      identifiants conservés.
- [ ] Le stem d'`imageid` applique NFKD, ASCII, minuscules, retire espaces et
      points, puis tout caractère hors `[a-z0-9_-]`; un stem vide devient
      `sans-id`.
- [ ] Deux identifiants distincts produisant le même `imageid` bloquent le
      traitement sans suffixe ni écrasement.
- [ ] Le web bloque cette collision avant aperçu et export CSV, même sans ZIP
      images, avec `SIRCOM_IMAGE_ID_COLLISION` et uniquement les emplacements de
      cellules concernés dans le détail public.
- [ ] La voie scriptée termine avec un code non nul et le même code stable,
      sans recopier les identifiants dans le journal technique.

## Hors périmètre

- Décider si l'alias `ID` apparaît réellement dans le jeu officiel.
- Reconstituer des zéros initiaux absents de la valeur Excel.
- Assouplir ou modifier la normalisation `imageid` du parcours web.
- Modifier les règles d'union ou de priorité de la fusion web.
- Nettoyer ou restaurer les modifications locales préexistantes.
- Traiter le jeu officiel.

## Preuve attendue

- test rouge reproduisant la suppression alphanumérique avant correction ;
- tests ciblés de l'extracteur et du vérificateur ;
- tests ciblés du diagnostic, de la normalisation et de l'aperçu CSV web ;
- contrôle du nombre de lignes et des identifiants synthétiques conservés ;
- `uv run --frozen --extra test pytest --cov=sircom2026 --cov-report=term-missing -q` ;
- commandes Ruff du dépôt ;
- `git diff --check`.

## Sources locales

- `AGENTS.md`
- `docs/specs/2026-07-28-fiabilisation-parcours-sircom-2026.md`
- `re-run-old-script-2026/00-extract_departement_to_sircom.py`
- `re-run-old-script-2026/13-verify_data_integrity.py`
- `re-run-old-script-2026/sircom2026_rules.py`
- `sircom2026/excel_diagnostic.py`
- `sircom2026/transform.py`
- `sircom2026/csv_preview.py`
- `tests/test_excel_diagnostic.py`
- `tests/test_csv_preview.py`
