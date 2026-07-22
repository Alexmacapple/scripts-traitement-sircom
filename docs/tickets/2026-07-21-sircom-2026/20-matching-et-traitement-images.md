# 20 - Matching et traitement images

Statut : `ready-for-agent`

Dépend de : 12, 18, 19.

À construire : associer une image principale aux dossiers, résoudre les
ambiguïtés et produire les JPG finaux.

Critères d'acceptation :

- [ ] Le matching tente d'abord le nom original si disponible.
- [ ] Le fallback par `id_dossier` est signalé.
- [ ] Les tolérances automatiques couvrent casse, espaces et extension
      équivalente.
- [ ] Les ressemblances partielles fortes deviennent suggestions à valider, pas
      choix automatique.
- [ ] Les ambiguïtés bloquent jusqu'à résolution manuelle.
- [ ] Les résolutions manuelles sont persistées et invalident le package si
      nécessaire.
- [ ] Les images manquantes et non référencées sont listées sans bloquer le CSV.
- [ ] Les images finales sont JPG, largeur max 350 px, qualité 100, DPI 300,
      fond blanc si transparence et EXIF appliqué.
- [ ] Le nom final suit `dossier-{id-normalise}.jpg`, avec minuscules,
      suppression des points et espaces, et conservation des tirets.
- [ ] Le dossier final s'appelle `export-jpg-resize/`.
- [ ] Les images sources viennent uniquement du zip uploadé, jamais d'un ancien
      dossier local.
- [ ] Tests pour exact, tolérant, fallback, ambigu, manquant, non référencé et
      conversion.

Hors périmètre :

- plusieurs images principales ;
- images en sous-dossiers.

Preuve attendue :

- tests image avec fixtures synthétiques.

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z04-001`.

Titre ShipGuard : collisions de noms JPG finaux non détectées pour des
`id_dossier` normalisés identiques.

Décision appliquée : le matching images ne change pas la règle de nommage
`dossier-{id-normalise}.jpg`. Il détecte désormais les collisions de nom final
avant toute association source, marque les dossiers concernés en `ambiguous`
avec `match_level` à `final_name_collision`, et bloque le matching tant que les
identifiants d'entrée produisent le même fichier final.

Preuve locale :

- test ciblé collision :
  `tests.test_image_matching.ImageMatchingRulesTest.test_final_jpg_name_collision_blocks_matching`,
  `OK` ;
- suite matching images : `tests.test_image_matching`, `7 tests`, `OK` ;
- suite consommateurs matching :
  `tests.test_image_matching tests.test_package tests.test_reports tests.test_csv_preview`,
  `13 tests`, `OK`.

Limite : le correctif bloque les collisions au lieu de générer un suffixe
automatique. Cette décision préserve le contrat de nommage du ticket et évite
de masquer deux dossiers métier qui convergent vers le même nom InDesign.

Finding traité : `SG-001`, origine stable `r1-z04-002`.

Titre ShipGuard : le script 2025 cherche les images sources avec le nom cible
`imageid`.

Décision appliquée : le script historique `scripts-2025/10-process-images.py`
sépare désormais le nom source et le nom final. Il lit la colonne photo source
du fichier `7-add-pathimg.xlsx` pour chercher l'image réellement uploadée, puis
utilise `imageid` uniquement comme nom JPG final.

Preuve locale :

- test ciblé script 2025 :
  `tests.test_scripts_2025_process_images`, `1 test`, `OK` ;
- suite complète : `178 tests`, `OK`, `2 skipped`.

Limite : la correction porte sur le script 2025 local. Elle ne change pas le
contrat 2026 du zip images, qui reste couvert par le worker et les artefacts du
lot.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
