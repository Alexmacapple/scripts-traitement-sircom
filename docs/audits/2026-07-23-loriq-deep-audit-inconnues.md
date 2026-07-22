# Audit Loriq des inconnues restantes

Date locale : 2026-07-23.

## Résultat

Le dernier passage Loriq sur une copie jetable du commit
`485189b0267d4683eeee779048c5942c79cf4fde` ne confirme aucun bug.

Synthèse Loriq :

- `finding_count=0` ;
- `unknown_count=14` ;
- `audited_project_changed=false` ;
- 7 lanes inspectées ;
- 92 fichiers probés par reçus ;
- 0 lane planifiée restante ;
- 0 périmètre de lane sauté.

L’état `incomplete` vient uniquement du cap déterministe du détecteur parent à
65 536 octets. Les reçus de lanes ont lu les fichiers inspectés avec un cap à
1 Mio et les ont liés au snapshot Loriq.

## Preuves

Commandes exécutées depuis le clone Loriq :

```bash
.venv/bin/python runtime/deep_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-unknowns.quYX53/madeinfrance \
  --deep-audit-only \
  --child-file-cap 40 \
  --out /private/tmp/madeinfrance-loriq-unknowns.quYX53/deep-audit-plan.json

.venv/bin/python runtime/deep_audit.py \
  --poc-repo /private/tmp/madeinfrance-loriq-unknowns.quYX53/madeinfrance \
  --deep-audit-only \
  --child-file-cap 40 \
  --receipts /private/tmp/madeinfrance-loriq-unknowns.quYX53/deep-audit-receipts.json \
  --out /private/tmp/madeinfrance-loriq-unknowns.quYX53/deep-audit-reconciled.json
```

Rapport reconcilié :

- `generated_at=2026-07-22T22:41:59Z` ;
- `target_snapshot_sha256=0b4ad9f0610294b6fe8647355806f3e200bd4220fc212f82f9fed1f6969532d6`.

## Classification

| Classe | Chemins | Verdict | Suite utile |
| --- | --- | --- | --- |
| Assets DSFR et polices livrés avec l'application | `sircom2026/static/dsfr/1.14.4/dsfr.min.css`, `dsfr.module.min.js`, `dsfr.nomodule.min.js`, `Spectral-*.woff`, `Spectral-*.woff2` | Normal : fichiers minifiés ou binaires au-delà du cap parent. | Ne pas les refactorer. Vérifier seulement lors d'une mise à jour DSFR ou d'une politique d'intégrité des assets. |
| Fichiers générés ou de vérification | `uv.lock`, `visual-tests/_review-template.html`, `visual-tests/build-review.mjs` | Normal : fichiers volumineux attendus. | Garder `uv.lock`. Découper le harnais visual-tests seulement si sa maintenance devient un problème. |
| Sources applicatives volumineuses | `sircom2026/app.py`, `sircom2026/database.py`, `sircom2026/templates/index.html` | Pas un bug confirmé, mais signal de maintenabilité. Les fichiers ont été probés par reçus et les tests passent. | À découper au prochain changement substantiel : routes FastAPI, accès base, partials de template. |
| Documentation source volumineuse | `docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md` | Normal pour une source de cadrage historique, mais peu ergonomique. | Scinder si ce document redevient une source active de décision. |

## Décision

Ne pas ouvrir de chantier code sur ces inconnues seules : aucun comportement
défaillant n'est prouvé. La prochaine amélioration utile est un refactor ciblé
des grands fichiers applicatifs quand une demande fonctionnelle les touche.

## Limites

- Les rapports bruts Loriq sont stockés en `/private/tmp`, pas versionnés.
- L'audit ne remplace pas une revue humaine des assets tiers DSFR.
- Le wiki ne contenait pas de why-context spécifique à `madeinfrance` ou
  `Loriq`; seules des règles générales de confinement d'audit ont été trouvées.
