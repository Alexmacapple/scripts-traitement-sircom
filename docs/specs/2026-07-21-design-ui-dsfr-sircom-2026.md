# Design UI DSFR Sircom 2026

Date : 2026-07-21

## Sources

- `docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `/Users/alex/Claude/design-systems/dsfr/DESIGN.md`
- `/Users/alex/Claude/design-systems/dsfr/tokens.yaml`
- `/Users/alex/Claude/.claude/skills/dsfr-components/SKILL.md`
- références locales DSFR : `page-shell.md`, `components-routing.md`,
  `forms-models.md`, `verification.md`

## Problème

Les specs cadrent le métier, l'architecture et les tickets, mais pas encore le
contrat UI DSFR détaillé. Sans ce document, un agent peut transformer le ticket
01 en landing page, inventer des composants proches du DSFR ou promettre une
conformité RGAA non vérifiée.

## Position V1

- L'interface est un outil opérationnel, pas une page marketing.
- Le front V1 utilise FastAPI, templates Jinja, assets DSFR statiques et
  JavaScript minimal.
- Aucune SPA React, Vue ou Angular n'est prévue en V1.
- Version DSFR cible : 1.14.4, à figer dans les assets statiques du projet.
- Mode marque Sircom 2026 : header DSFR avec Marianne et bloc marque
  République Française, décision projet explicite pour cette V1 locale.
- Mention autorisée : "interface alignée sur les composants DSFR utilisés".
- Mentions interdites sans audit : "conforme DSFR", "conforme RGAA",
  "prêt publication service public".

## Shell de page

Chaque page rendue doit fournir :

- `html lang="fr"` ;
- un lien d'évitement vers le contenu principal ;
- un `header` DSFR sobre avec bloc marque Marianne, sans navigation technique ;
- un `main` avec identifiant stable ;
- un `footer` DSFR minimal ;
- une navigation active lisible dans le détail du lot ;
- aucun lien `href="#"` ;
- aucun chemin disque interne ;
- des titres hiérarchisés sans saut incohérent.

Le ticket 01 livre seulement le shell, la navigation de base et une zone de
contenu. Il ne livre pas les écrans métier complets.

## Écrans V1

| Écran | Rôle | Tickets |
|---|---|---|
| Accueil lots | Voir les lots, créer un lot, voir état global et stockage | 04, 23 |
| Détail lot | Timeline, statut, actions possibles, problèmes | 04, 06 |
| Upload Excel | Déposer un fichier, voir limites et erreurs structurées | 09, 11 |
| Diagnostic Excel | Voir blocages, alertes, onglets, colonnes, actions correctives | 10, 11 |
| Mapping | Sélectionner colonnes, éditer noms CSV, voir provenance | 12 |
| Tri | Proposer région/département, confirmer ou conserver ordre Excel | 15 |
| Aperçu CSV | Voir en-têtes finaux, premières lignes, suppressions, alertes | 17 |
| Upload images | Déposer zip, suivre inspection, voir refus | 18 |
| Matching images | Résoudre ambiguïtés, continuer sans images, voir absences | 20 |
| Package | Valider package, télécharger artefacts, voir manifeste | 22 |
| Exploitation | Voir disque, rétention, supprimer un lot | 23 |

## Parcours utilisateur

Le détail d'un lot expose un parcours centré sur les besoins Sircom et déroule
l'orchestration de bout en bout. Le menu principal du lot contient les 13 étapes
séquentielles, avec une seule étape active par page :

1. Déposer l'Excel ;
2. Vérifier l'Excel ;
3. Choisir les colonnes ;
4. Fusionner les onglets ;
5. Normaliser les contenus ;
6. Valider le tri ;
7. Vérifier le CSV InDesign ;
8. Prévisualiser le CSV ;
9. Déposer le zip images ;
10. Inspecter les images ;
11. Associer les images ;
12. Récupérer les rapports ;
13. Préparer le package final.

Chaque page d'étape suit la pyramide inversée : statut et action attendue en
premier, détail utile ensuite, historique technique en accordéon à la fin. Les
étapes automatiques sont présentées comme traitements locaux orchestrés par le
worker, sans bouton de validation artificiel.

Le stepper DSFR du détail de lot porte la progression séquentielle sur 13
étapes. Les anciennes phases métier peuvent rester des libellés internes ou de
synthèse, mais elles ne remplacent pas la navigation étape par étape.

Les accès `API` et `Santé` sont des liens techniques de pied de page. Ils ne
doivent pas être exposés dans le header ni dans le menu de parcours utilisateur.

## Composants DSFR attendus

- Alertes DSFR pour problèmes bloquants, alertes et informations.
- Badges DSFR pour statuts lot, étape et sévérités.
- Boutons DSFR pour actions explicites : créer, valider, relancer, annuler,
  supprimer, télécharger.
- Formulaires DSFR pour uploads, mapping, tri et validations.
- Tableaux DSFR ou tables HTML structurées pour mapping, aperçu CSV et listes.
- Onglets DSFR uniquement si plusieurs vues d'un même lot sont disponibles.
- Accordéons ou détails dépliables pour informations techniques.
- Indicateur de progression accessible pour traitements de fond.

Si un composant DSFR officiel couvre le besoin, ne pas créer un composant
custom équivalent.

## États visibles

Chaque étape métier doit avoir une représentation UI pour :

- non démarrée ;
- prête ;
- en cours ;
- action requise ;
- bloquée ;
- terminée ;
- terminée avec alertes ;
- échouée ;
- annulée ;
- ignorée.

Les actions disponibles sont dérivées de l'état persistant, jamais d'un état
visuel local seul.

## Messages

Les messages visibles suivent la structure :

- titre court ;
- cause compréhensible ;
- emplacement métier si disponible ;
- action attendue ;
- détails techniques dépliables si utile.

Les détails techniques ne doivent pas exposer de valeur métier sensible, de
chemin disque interne ou de trace brute.

## Formulaires

- Chaque champ a un label explicite.
- Les aides et erreurs sont reliées au champ par attributs accessibles.
- Les champs `required` ou `pattern` ne sont utilisés que si le comportement
  navigateur ne dégrade pas le parcours ; sinon validation serveur et message
  DSFR.
- Après erreur de validation, le focus revient sur le premier problème ou sur le
  résumé d'erreurs.
- Les doubles soumissions sont neutralisées par idempotence backend, pas
  seulement par désactivation visuelle du bouton.

## Responsive

- Les écrans doivent rester utilisables en desktop et mobile.
- Les tableaux larges peuvent utiliser défilement horizontal explicite avec
  intitulé et alternative synthétique.
- Les barres d'actions critiques restent proches du contenu concerné.
- Aucun texte ne doit déborder d'un bouton, badge ou panneau.

## Accessibilité et vérification

Minimum par ticket UI :

- tests `TestClient` vérifiant landmarks, liens d'évitement et absence de
  `href="#"` ;
- vérification HTML des labels de formulaire ;
- vérification des états d'erreur et d'action requise ;
- capture Playwright desktop et mobile dès qu'une vraie page métier est créée ;
- pas de revendication RGAA sans audit dédié.

## Hors périmètre V1

- Design graphique final d'un service public exposé publiquement.
- Audit RGAA complet.
- SSO ou authentification VPS réelle.
- Composants DSFR complexes non nécessaires au flux Sircom.

## Questions ouvertes bornées

- Conditions de publication publique du bloc marque République Française.
- URLs légales finales du footer.
- Audit RGAA complet si l'application sort du poste local vers une publication
  plus large.
