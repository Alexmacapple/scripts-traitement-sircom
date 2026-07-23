# Prompt GLM - contre-revue indépendante en mode Fable Flavien

Ce prompt est destiné à un agent GLM chargé de relire le projet Made in France
indépendamment de notre propre revue, puis de croiser les conclusions pour
aider à choisir le prochain chantier technique.

```md
Mission : fais une contre-revue de code complète et indépendante du projet `/Users/alex/Claude/projets-heberges/madeinfrance`, puis aide à décider quel chantier technique prioriser.

Contexte : une première revue interne a déjà été produite dans `docs/audits/2026-07-23-revue-code-fable-flavien.md`. Elle donne une note de 15/20 et identifie notamment des risques sur les bornes Excel/images, la pression mémoire/disque, l'annulation des traitements lourds, la taille du routeur lots, les tests visuels, l'accessibilité et la dérive README/TODO.

Pourquoi : je veux une revue indépendante pour croiser les sources, repérer nos angles morts, confirmer ou contredire les risques, et décider du chantier à lancer maintenant. Ne cherche pas à confirmer notre rapport : cherche la vérité terrain du dépôt.

Méthode obligatoire :
1. Phase aveugle : commence par auditer le dépôt sans lire `docs/audits/2026-07-23-revue-code-fable-flavien.md`. Note ton verdict, ta note provisoire et tes principaux risques.
2. Phase de croisement : lis ensuite `docs/audits/2026-07-23-revue-code-fable-flavien.md`, compare-le à ta revue aveugle, puis indique précisément ce que tu confirmes, ce que tu contestes, ce qui manque et ce qui change dans ta note finale.
3. Phase décision : recommande le prochain chantier à faire, avec périmètre, critères d'acceptation, tests à lancer et éléments à ne pas traiter dans ce chantier.

Sources à lire réellement avant de juger :
- `AGENTS.md`, `README.md`, `CLAUDE.md`, `TODO.md`, `CHANGELOG.md` ;
- `pyproject.toml`, `uv.lock`, `.github/workflows/` ;
- les tests unitaires, intégration et Playwright ;
- les modules applicatifs principaux dans `sircom2026/` ;
- les templates, CSS, JS, scripts et workflows visuels ;
- les références métier 2025 et 2026 citées par `AGENTS.md`.

Si une source importante n'est pas lue, marque-la `non vérifié` et explique l'impact sur ton jugement.

Point d'attention important : le dépôt peut être nettement plus avancé que son README et son TODO. Des commits et modules couvrent déjà matching images, rapports, package, purge et plusieurs refactorings, alors que README/TODO peuvent encore les annoncer comme à faire. README.md et TODO.md sont donc à lire, mais ne doivent pas être traités comme preuve d'absence fonctionnelle.

Consigne de jugement sur la documentation :
- juge d'abord ce que le dépôt fait réellement : code, tests, workflows, commandes, artefacts générés ;
- utilise README/TODO pour détecter les écarts de documentation, pas pour déduire automatiquement qu'une fonctionnalité manque ;
- quand documentation et code divergent, cite les deux sources et tranche explicitement : `code vérifié`, `documentation en retard`, `incertitude`, ou `fonction réellement absente` ;
- dans la note, pénalise cette dérive dans `Documentation, installation, exploitation`, pas dans `Robustesse fonctionnelle` sauf preuve locale d'un comportement cassé.

Limites :
- Ne modifie aucun fichier.
- Ne lance aucune commande destructive.
- Ne commite rien.
- Ne juge pas depuis l'apparence du dépôt seulement.
- Ne donne pas de note sans preuves locales.
- Ne cite pas de données sensibles si tu en croises.

Autonomie : mode Flavien / mandat entrepreneur. Construis ton propre chemin d'audit, cherche les angles morts, priorise les risques réels, puis rends un verdict exploitable. Ne t'arrête que si le dépôt est inaccessible ou si une preuve indispensable manque.

Effort : high. Le livrable doit être sérieux, sourcé et utile pour arbitrer.

Vérification attendue :
- Cite les fichiers et lignes quand tu affirmes un problème.
- Indique les commandes lancées et leur résultat décisif.
- Sépare clairement : faits vérifiés, hypothèses, non vérifié.
- Si les tests ne tournent pas, explique pourquoi et l'impact sur la note.
- Si tu n'as pas lancé une commande importante, indique pourquoi.

Grille de notation sur 20 :
- Architecture et séparation des responsabilités : /4
- Maintenabilité, lisibilité, taille des modules : /3
- Robustesse fonctionnelle et gestion des erreurs : /3
- Tests, couverture utile et vérifiabilité : /3
- Sécurité, données, dépendances, secrets : /2
- UX, accessibilité, cohérence interface : /2
- Documentation, installation, exploitation : /2
- Hygiène Git, CI, packaging : /1

Format de sortie :
1. Verdict court : note finale `/20` + phrase de synthèse.
2. Verdict aveugle initial : note provisoire, risques majeurs, avant lecture de notre rapport.
3. Tableau de notation : critère, note, justification, preuve.
4. Top 10 des risques ou dettes, triés par impact.
5. Écarts documentation / état réel :
   - fonctionnalités annoncées comme à faire mais observées dans le code ;
   - preuves locales ;
   - impact sur la note ;
   - ce qu'il faut mettre à jour dans README/TODO.
6. Croisement avec notre revue :
   - points confirmés ;
   - points contestés ;
   - risques manqués par notre revue ;
   - risques de notre revue que tu juges surestimés ;
   - changement éventuel de note après lecture.
7. Décision chantier :
   - chantier recommandé maintenant ;
   - pourquoi ce chantier plutôt que les autres ;
   - périmètre exact ;
   - critères d'acceptation ;
   - commandes de vérification ;
   - hors périmètre volontaire.
8. Points forts réels, uniquement s'ils sont prouvés.
9. Priorités recommandées :
   - à faire maintenant ;
   - à faire ensuite ;
   - à ne pas faire pour l'instant.
10. Limites de l'audit : fichiers non lus, commandes non lancées, incertitudes.

Ton style : direct, exigeant, utile. Pas de complaisance. Pas de jargon inutile.
```
