# Audit d'accessibilité — Site public Sircom 2026

- **Date** : 24 juillet 2026
- **Mise à jour** : 24 juillet 2026 — défaut unique corrigé, vérifié par deux passes de scan indépendantes
- **Statut** : 0 violation axe-core sur les 9 pages
- **Périmètre** : application web locale `http://127.0.0.1:8000` (FastAPI, interface DSFR 1.14.4)
- **Référentiel** : WCAG 2.2 niveau AA
- **Pages auditées** : 9 (accueil, 3 écrans de workflow, 5 pages d'information)
- **Outils** : axe-core 4.10 injecté dans Chrome réel via `agent-browser` ; parcours Tab clavier ; inspection DOM et computed styles (`::before` compris)
- **Constats excluant `/docs`** : la page `/docs` (Swagger UI) est un explorateur d'API réservé aux développeurs, hors périmètre « site public ».

---

## 1. Synthèse exécutive

**9 pages auditées — 0 violation axe-core après correction.**

Le site public est **conforme WCAG 2.2 AA** sur l'ensemble du périmètre testable automatiquement. Aucun défaut bloquant, aucun défaut majeur. Le socle DSFR est bien exploité. Le défaut mineur initial (doublon de landmark sur `/lots/{id}/images`) a été corrigé et vérifié par deux passes de scan indépendantes.

| Page / vue | axe-core | h1 | Hiérarchie titres | Interactifs sans nom | Focus clavier |
|---|---|---|---|---|---|
| `/` (accueil + panels : sources, lots, vue d'ensemble, détail lot) | 0 | unique | OK | 0 | conforme |
| `/lots/{id}/excel` | 0 | « Traitement Excel du lot… » | OK | 0 | conforme |
| `/lots/{id}/images` | 0 *(corrigé)* | « Traitement images du lot… » | OK | 0 | conforme |
| `/lots/{id}/export` | 0 | « Export final du lot… » | OK | 0 | conforme |
| `/plan-du-site` | 0 | « Plan du site » | OK | 0 | — |
| `/accessibilite` | 0 | « Accessibilité » | OK | 0 | — |
| `/mentions-legales` | 0 | « Mentions légales » | OK | 0 | — |
| `/donnees-personnelles` | 0 | « Données personnelles » | OK | 0 | — |
| `/gestion-cookies` | 0 | « Gestion des cookies » | OK | 0 | — |

Le défaut initial `landmark-unique` sur `/lots/{id}/images` est **corrigé** (section 3) et vérifié par deux passes de scan indépendantes (section 6, sous-section « Convergence des preuves »).

---

## 2. Points forts (transverses à toutes les pages)

- **Langue** : `lang="fr"` sur `<html>` partout.
- **Titres de page** : format RGAA « Page - Sircom 2026 » (ex. `Plan du site - Sircom 2026`). Conforme au critère RGAA 8.5.
- **Liens d'évitement (skip links)** présents sur toutes les pages — jusqu'à 5 sur les pages de workflow (contenu, étapes du lot, étape active, détails techniques, pied de page), en tête de DOM.
- **Statuts intégrés aux liens d'onglets** : « Traitement Excel À corriger », « Traitement images Partiel », « Export final À venir ». L'information de statut **n'est pas portée par la couleur seule** (WCAG 1.4.1) — elle est doublée d'un texte dans le nom accessible.
- **Focus visible** : le pattern DSFR `fr-enlarge-link` reporte un cadre `outline: 2px solid` (rgb 10,118,246) sur le pseudo-élément `::before` du lien, couvrant toute la card. Outline standard sur les autres interactifs (nav, formulaire, footer).
- **Aucune image sans `alt`**, **aucun interactif sans nom accessible**, **aucun piège de focus**.
- **Landmarks** propres et cohérents : `header[role=banner]`, `nav` principale, `nav` fil d'Ariane (« vous êtes ici »), `main#contenu`, `footer[role=contentinfo]`.
- **Contraste** : 0 violation réelle mesurée par axe-core sur l'ensemble des pages (les éléments signalés « incomplete » sont des fonds incertains non résolvables, sans ratio insuffisant avéré).

---

## 3. Constat détaillé — défaut unique (corrigé)

### `/lots/{id}/images` — doublon de landmark

| Règle axe-core | Sévérité | Référentiel | Localisation |
|---|---|---|---|
| `landmark-unique` | Mineure | Bonne pratique ARIA (proche RGAA 9.1, **pas un critère WCAG formel**) | `templates/partials/workflow_view.html:62` + `templates/partials/workflow_images.html:3` |

**Description** : sur la page de traitement images, deux éléments `<section>` deviennent des landmarks de type `region` (via `aria-labelledby`) et portent **le même nom accessible** (« Associer et traiter les images ») :

- `workflow_view.html:62` — `<h3 id="lot-workspace-title">{{ active_step.label }}</h3>` (section `#lot-workspace`)
- `workflow_images.html:3` — `<h3 id="image-workflow-title">{{ active_step.label }}</h3>` (section secondaire)

Quand une étape images est active, `active_step.label` prend la même valeur dans les deux sections. axe-core signale alors la duplication de landmark.

**Pourquoi `/excel` et `/export` ne sont pas concernés** : leurs régions ont des intitulés distincts (« Diagnostiquer l'Excel », « Vérifier l'Excel », « Bloquant : 8 points », « Alerte : 3 points »), donc pas de doublon.

**Impact** : navigation par landmarks au lecteur d'écran légèrement confuse (deux régions de même nom dans la même page). Aucun impact pour la navigation souris ou au Tab.

**STATUT : CORRIGÉ le 24 juillet 2026.**

Correction appliquée (option 1) — `templates/partials/workflow_view.html:62` :

```jinja
<h3 id="lot-workspace-title">Espace de travail — {{ active_step.label if active_step else "Où en est le lot ?" }}</h3>
```

La région `#lot-workspace` porte désormais le nom accessible « Espace de travail — {label} », distinct de la section de détail qui conserve « {label} ». L'ID `#lot-workspace-title` est inchangé, donc le skip link `skiplinks.html:24` reste fonctionnel.

**Preuve** (scan axe-core après correction) :
- `/lots/{id}/images` (lot `lot_0e1e543a`) : 0 violation (avant : 1 `landmark-unique`).
- `/lots/{id}/images` (lot `lot_aba27bdb`, passe de convergence) : 0 violation.
- Titre rendu confirmé : « Espace de travail — Associer et traiter les images ».

---

## 4. Point de vérification `aria-live` — vérifié, déjà couvert

**STATUT : VÉRIFIÉ, aucune correction nécessaire.**

Lecture réelle de `sircom2026/static/app.js` et des templates : le routing est **synchrone** (`window.location.assign` après chaque action réussie) — il n'y a pas de mise à jour DOM asynchrone du « statut du lot » qui nécessiterait une région `aria-live` dédiée. Les annonces dynamiques qui existent sont déjà couvertes :

- **Erreurs dynamiques** : `app.js` (fonction `showError`) pousse dans une `messageBox` porteuse de `role="alert"` (`templates/index.html:45`) → annonce assertive implicite.
- **Alertes de progression et de statut** : 40+ occurrences `role="status"` / `role="alert"` / `aria-live="polite"` dans les partials (`workflow_excel`, `workflow_details`, `workflow_csv`, `source_uploads`, `home_view`, etc.).

Le soupçon initial « aria-live potentiellement manquant » est donc **infirmé** par lecture du code.

---

## 5. Périmètre non couvert par cet audit

- **`/docs` (Swagger UI)** : explorateur d'API développeur, exclu du « site public ». Il présente 7 violations axe-core toutes internes à la bibliothèque Swagger UI (`html-has-lang`, contraste des tampons de version, `nested-interactive`, `target-size`, etc.) — non corrigeables dans le code Sircom sans remplacer le renderer.
- **Endpoints techniques** : `/health`, `/health/ready`, `/api/config/limits` (JSON, pas d'UI).
- **Tests lecteur d'écran réels** (VoiceOver / NVDA / JAWS) : non réalisés ici. L'inspection DOM/ARIA faite est un indicateur solide mais ne remplace pas un test utilisateur avec synthèse vocale.
- **Comportement dynamique** (`aria-live`, transitions d'état) : vérifié par lecture du code (section 4) — routing synchrone, `role="alert"` / `role="status"` déjà présents. Reste non testé au lecteur d'écran réel.

---

## 6. Méthodologie

- **Scan automatique** : injection de axe-core 4.10 (depuis CDN unpkg) dans un Chrome réel piloté par `agent-browser`, avec les tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, `best-practice`.
- **Navigation clavier** : séquences `Tab` réelles, capture de `document.activeElement` et de son `outline` calculé à chaque saut.
- **Lecteur d'écran (inspection)** : extraction des landmarks, de la hiérarchie de titres, des noms accessibles, des images et des champs de formulaire.
- **Vérification du focus DSFR** : lecture du `::before` via `getComputedStyle(el, '::before')` pour ne pas faux-positiver sur les liens `fr-enlarge-link` (le cadre de focus est reporté sur le pseudo-élément, pas sur le `<a>`).

### Note d'honnêteté

Un test intermédiaire a initialement conclu à un focus invisible sur 6 liens `fr-enlarge-link`. **Constat infirmé** après vérification du `::before` : le focus est visible (cadre 2px sur toute la card). Ce faux positif est un angle mort classique des validateurs qui ne lisent que l'élément et non son pseudo-élément.

### Convergence des preuves

Le verdict final est confirmé par **deux passes de scan indépendantes** :

| | Passe Claude (cet audit) | Passe agent GLM ax |
|---|---|---|
| Moteur | `agent-browser` + axe-core 4.10 | `playwright` / `ay11` |
| Lot testé | `lot_0e1e543a` (+ `lot_aba27bdb` en convergence) | `lot_aba27bdb` |
| `/lots/{id}/excel` | 0 | 0 |
| `/lots/{id}/images` | 0 (après fix) | 0 |
| `/lots/{id}/export` | 0 | 0 |

Deux lots, deux moteurs, deux agents → verdict convergent : **0 violation** sur les pages workflow après correction.

---

## 7. Conclusion

Le site public Sircom 2026 est **solide et homogène** sur l'accessibilité : 9 pages auditées, **0 violation axe-core** après correction du défaut mineur initial. Le socle DSFR est bien exploité (skip links, statuts textuels, focus visible, structure sémantique, titres au format RGAA). Aucun défaut bloquant ni majeur.

**Défaut corrigé** : doublon de landmark `#lot-workspace` sur `/lots/{id}/images` (section 3) — fix appliqué, prouvé par deux passes de scan indépendantes.

**Point vérifié** : régions `aria-live` déjà couvertes, routing synchrone (section 4).

**Reste non couvert** : test lecteur d'écran réel (VoiceOver / NVDA / JAWS) et audit expert manuel RGAA complet pour une déclaration de conformité officielle.
