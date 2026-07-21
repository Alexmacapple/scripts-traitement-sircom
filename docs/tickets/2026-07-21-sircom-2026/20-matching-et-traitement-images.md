# 20 - Matching et traitement images

Statut : `a-recadrer`

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

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
