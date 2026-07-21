# 18 - Upload zip images et inspection sécurisée

Statut : `done`

Dépend de : 05, 08.

À construire : téléverser un zip images, l'inspecter sans extraction dangereuse
et produire un bilan structuré.

Critères d'acceptation :

- [x] Un seul zip images est accepté par lot.
- [x] L'extension et la signature zip sont contrôlées.
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

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
- [Contrats complémentaires](../../specs/2026-07-21-contrats-implementation-sircom-2026.md)
