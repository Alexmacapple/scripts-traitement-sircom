# 22 - Package final, manifeste et téléchargements

Statut : `a-corriger`

Dépend de : 17, 20, 21.

À construire : produire le package zip final, son manifeste et les
téléchargements des artefacts principaux.

Critères d'acceptation :

- [ ] La génération du package demande une validation humaine.
- [ ] La génération du package est exécutée par le worker, pas dans la requête
      HTTP.
- [ ] Le package téléchargeable est nommé `sircom-2026-lot-{lot_id}.zip`.
- [ ] Le package contient exactement les artefacts racine suivants en V1 :
      `sircom-indesign-utf16.csv`, `rapport-metier.md`,
      `rapport-technique.json`, `mapping-utilise.json`, `manifest.json` et le
      dossier `export-jpg-resize/`.
- [ ] Le manifeste liste les artefacts avec rôles, tailles et empreintes.
- [ ] Les chemins `@pathimg` visent `SIRCOM_INDESIGN_IMAGE_ROOT`.
- [ ] Le package n'est pas produit s'il reste des problèmes bloquants ouverts.
- [ ] Le package n'est pas produit si les artefacts ou fingerprints requis sont
      obsolètes.
- [ ] Un package sans images est possible seulement après alerte visible et
      décision explicite quand le flux images est ignoré ou terminé avec alertes.
- [ ] Les fichiers principaux peuvent être téléchargés séparément si disponibles.
- [ ] Tests pour contenu zip, manifeste et téléchargement par `artifact_id`.

Hors périmètre :

- validation réelle dans InDesign ;
- purge de rétention.

Preuve attendue :

- test package inspectant le contenu du zip.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
