# 18 - Upload zip images et inspection sécurisée

Statut : `done`

Dépend de : 05, 08.

À construire : téléverser un zip images, l'inspecter sans extraction dangereuse
et produire un bilan structuré.

Critères d'acceptation :

- [x] Un seul zip images est accepté par lot.
- [x] L'extension et la signature zip sont contrôlées.
- [x] Les entrées zip chiffrées sont refusées avant le matching images.
- [x] Les tailles compressée, décompressée, nombre de fichiers et taille par
      image sont contrôlées.
- [x] Les chemins absolus, `..`, noms vides et caractères de contrôle sont
      refusés.
- [x] Les doublons de noms après normalisation Unicode/casse sont détectés et
      signalés.
- [x] Les images à la racine sont listées.
- [x] Toute image placée dans un sous-dossier du zip est refusée en V1 avec
      message actionnable ; seuls les fichiers système explicitement ignorables
      (`__MACOSX/`, `.DS_Store`) peuvent être écartés sans bloquer.
- [x] Un zip sans image traitable produit une alerte non bloquante pour le CSV.
- [x] L'inspection nettoie le répertoire temporaire du lot en cas d'échec.
- [x] Un nouvel upload zip invalide le traitement images et le package.
- [x] Tests pour zip valide, signature invalide, traversal, sous-dossier seul,
      zip mixte racine/sous-dossier, doublons normalisés, zip vide et zip trop
      gros.

Hors périmètre :

- conversion image ;
- matching images/dossiers.

Preuve attendue :

- tests de sécurité zip.

Preuve produite :

- `.venv/bin/python -m unittest tests.test_image_upload`
- `.venv/bin/python -m unittest`
- `git diff --check`

## Complément rapport ShipGuard - 2026-07-22

Finding traité : `SG-001`, origine stable `r1-z02-002`.

Titre ShipGuard : les uploads valident le fichier avant de vérifier le lot
ciblé.

Décision appliquée : `POST /api/lots/{lot_id}/images` vérifie désormais
l'existence et la mutabilité du lot avant de préparer le zip temporaire ou de
valider son extension/signature. Un upload vers un lot absent ne crée plus de
répertoire temporaire de lot, et un upload vers un lot supprimé retourne
`409 SIRCOM_LOT_NOT_MUTABLE` avant toute inspection du fichier.

Preuve locale :

- suite uploads ciblée :
  `tests.test_excel_upload tests.test_image_upload`, `21 tests`, `OK` ;
- suite complète : `181 tests`, `OK`, `2 skipped`.

Limite : le précontrôle initial évite la lecture/préparation inutile du fichier,
mais la transaction d'upload conserve son contrôle métier interne pour rester
correcte en cas de changement concurrent du lot.

## Complément rapport ShipGuard - 2026-07-22 - entrée zip chiffrée

Finding traité : `SG-001`, origine stable `r1-z04-003`.

Titre ShipGuard : une image zip chiffrée peut passer l'inspection puis faire
échouer le worker de matching.

Décision appliquée : l'inspection images refuse désormais toute entrée non
ignorée dont `ZipInfo.flag_bits & 0x1` indique un contenu chiffré, avec le
problème bloquant `SIRCOM_IMAGE_ZIP_ENCRYPTED_ENTRY`. Le worker de matching
capture aussi `RuntimeError` pendant la lecture de l'entrée source et marque la
ligne en `conversion_failed` si un artefact ancien ou injecté arrive malgré
l'inspection.

Preuve locale :

- suite ciblée : `tests.test_image_upload tests.test_image_matching`,
  `21 tests`, `OK` ;
- suite complète : `185 tests`, `OK`, `2 skipped`.

Limite : les lots déjà inspectés avant `image-zip-inspection-v2` ne sont pas
réinspectés sans nouveau job ou nouvel upload ; le matching contient le filet de
sécurité pour ces cas.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
