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
- [ ] Les dates invalides ou absentes sont signalées et sortent vides.
- [ ] `id_dossier`, SIRET, téléphone, code postal, département et codes
      administratifs restent traités comme texte.
- [ ] Les zéros initiaux de ces champs texte sont conservés.
- [ ] Les valeurs vides restent vides et ne deviennent jamais `nan`, `NaT`,
      `None` ou `#N/A`.
- [ ] Les prix, montants et pourcentages ne sont pas corrigés sans règle
      explicite.
- [ ] Tests pour chaque règle de normalisation.

Hors périmètre :

- tri ;
- encodage CSV ;
- correction métier manuelle.

Preuve attendue :

- tests unitaires de normalisation.

---

Parent : [index des tickets Sircom 2026](../2026-07-21-tickets-implementation-sircom-2026.md)

Sources :

- [Contrat fonctionnel](../../specs/2026-07-21-contrat-fonctionnel-sircom-2026.md)
- [Orchestration](../../specs/2026-07-21-orchestration-sircom-2026.md)
- [Design architecture](../../specs/2026-07-21-design-architecture-web-sircom-2026.md)
