# Prompt Fable - vérification globale Sircom 2026

À utiliser dans un autre agent Fable 5.

```text
/goal Vérifie de bout en bout le cadrage Sircom 2026 et dis si l'on peut passer à l'implémentation sans trou majeur.

Mission :
Fais une passe globale de vérification sur le cadrage Sircom 2026. Ta destination n'est pas de réécrire les documents, mais de prouver si la chaîne cuisine-moi -> spécifications -> tickets est complète, cohérente, implémentable et suffisamment cadrée pour des agents d'implémentation. Cherche les trous dans la raquette, les contradictions, les zones d'ombre, les tensions LLM, les critères d'acceptation trop flous et les travaux non assignés à un ticket.

Pourquoi :
On veut démarrer l'implémentation ticket par ticket avec le moins de friction possible. Le résultat doit permettre de décider : on lance le ticket 01, on corrige quelques documents avant de coder, ou on doit recadrer une partie structurante.

Sources à lire réellement :
- `/Users/alex/Claude/projets-heberges/madeinfrance/AGENTS.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/cuisine-moi/2026-07-20-interface-web-sircom-2026.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/specs/2026-07-21-contrat-fonctionnel-sircom-2026.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/specs/2026-07-21-orchestration-sircom-2026.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/specs/2026-07-21-design-architecture-web-sircom-2026.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/tickets/2026-07-21-tickets-implementation-sircom-2026.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/README.md`
- tous les fichiers `/Users/alex/Claude/projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/[0-9][0-9]-*.md`
- `/Users/alex/Claude/projets-heberges/madeinfrance/docs/tickets/2026-07-21-sircom-2026/revue-connus-inconnus-avocat-du-diable.md`
- en contexte seulement : `README.md`, `TODO.md`, `CHANGELOG.md`

Limites :
- Ne touche pas au code applicatif.
- À part le rapport Markdown attendu, ne modifie aucun fichier. Si tu recommandes
  une correction, fournis un patch proposé ou une liste précise
  fichier/ligne/nouveau texte, mais n'applique rien.
- Ne modifie aucun fichier de données réel, Excel, zip, image, export, log ou artefact généré.
- Ne commite rien et ne pousse rien.
- Ne déplace pas les specs ni les tickets.
- Ne transforme pas une préférence personnelle en blocage.
- Ne demande pas mon avis sauf si une information absente empêche vraiment le verdict.
- Ne demande pas de raisonnement interne ; livre hypothèses, preuves, décisions et limites.

Autonomie :
Mode Flavien / mandat entrepreneur. Pars de la destination, construis toi-même le chemin de vérification, explore les sources utiles, cherche les angles morts, prends les initiatives réversibles qui améliorent la qualité de la revue, puis vérifie ton propre résultat. Tu peux faire des lectures, recherches locales, contrôles de liens, matrices de couverture et analyses de dépendances. Si tu trouves des corrections documentaires mineures et non controversées, propose-les clairement ; n'applique pas de modification structurante sans validation.

Effort :
xhigh. La tâche est multi-sources, structurante et sert de porte avant implémentation.

Ce que tu dois vérifier :
- Couverture : chaque décision importante du cuisine-moi et des specs est couverte par une spec et au moins un ticket.
- Cohérence : pas de contradiction entre contrat fonctionnel, orchestration, architecture, AGENTS.md et tickets.
- Implémentabilité : chaque ticket a une entrée claire, une sortie observable, des critères d'acceptation testables, un hors périmètre et une preuve attendue.
- Dépendances : le graphe des tickets est acyclique, la frontier initiale est correcte et aucun ticket aval ne dépend d'une décision non cadrée.
- Tensions LLM : pas de termes du type "à décider", "à préciser", "si possible", "ou équivalent", "faire au mieux", ni d'ambiguïtés qui forceraient un agent à inventer.
- Données et sécurité : pas de demande de commiter des données réelles ; uploads, zip, artefacts, logs, purge et chemins internes sont cadrés.
- CSV/InDesign : UTF-16 BOM, virgule, LF, cellules vides, `id_dossier`, `imageid`, `@pathimg`, nommage 2025 et référence CSV 2025 sont sans ambiguïté.
- Excel : multi-onglets, `id_dossier`, refus strict, diagnostics actionnables, Sircom1/Sircom2 et fichiers synthétiques sont correctement exploités.
- Images : zip source, racine du zip, absence non bloquante, ambiguïtés, noms finaux, formats, HEIC, EXIF, DPI, qualité et dossier `export-jpg-resize/` sont cadrés.
- Orchestration : SQLite, statuts, événements, problèmes, worker, leases, `run_id`, retry, invalidation, annulation et purge sont suffisamment définis.
- UI : DSFR comme référence visuelle, pas de conformité RGAA revendiquée, validations humaines et messages utilisateurs sont bien placés.
- Exploitation : rétention, suppression immédiate, indicateurs disque, trace anonymisée et futur VPS ne créent pas d'impasse V1.

Livrable attendu :
Produis un rapport Markdown dans :
`/Users/alex/Claude/projets-heberges/madeinfrance/docs/2026-07-21-verification-globale-sircom-2026.md`

Structure du rapport :
Ajoute tout en haut du rapport un bloc `Décision actionnable` avec :
- Verdict :
- Frontier exacte :
- Nombre de corrections bloquantes :
- Nombre de corrections mineures :
- Fichiers à modifier avant ticket 01 :
- Ticket 01 lançable maintenant : oui/non + raison.

Puis structure le rapport ainsi :
1. Verdict court : `GO ticket 01`, `GO avec corrections mineures`, ou `STOP avant implémentation`.
2. Résumé exécutif en 5 à 10 lignes.
3. Matrice de couverture : cuisine-moi/specs -> tickets.
4. Findings classés par sévérité : bloquant, important, mineur.
5. Zones d'ombre restantes : uniquement celles qui changent l'implémentation.
6. Tensions LLM restantes : formulation exacte, fichier, ligne, risque, correction proposée.
7. Vérification ticket par ticket : verdict `prêt`, `à corriger`, ou `à recadrer`.
8. Recommandation finale : prochaine action concrète.
9. Preuves : fichiers lus, commandes lancées, limites non vérifiées.

Critères de réussite :
- Chaque finding cite un fichier et une ligne.
- Si aucun trou majeur n'est trouvé, dis-le clairement et explique pourquoi.
- Si une zone d'ombre est volontairement bornée par un ticket, ne la classe pas comme blocage.
- Si tu affirmes "tout est couvert", fournis la matrice qui le prouve.
- Si tu affirmes "prêt à implémenter", précise la frontier exacte.
- Si quelque chose n'a pas été vérifié, écris `non vérifié` et pourquoi.

Communication :
Commence par le résultat. Sois direct, pas rassurant par défaut. Distingue fait, hypothèse et jugement. Ne produis pas de grande prose si un tableau ou une liste courte prouve mieux le point.
```
