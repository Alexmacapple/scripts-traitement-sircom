# Changelog

## 2026-07-20

- Clonage et reprise du dépôt de scripts Sircom.
- Archivage des scripts historiques dans `scripts-2025/` et adaptation de l'orchestrateur.
- Ajout de `AGENTS.md` comme source locale de consignes agent.
- Ajout de `TODO.md` pour suivre les tâches de cadrage et d'implémentation.
- Cadrage de l'interface web Sircom 2026 dans `cuisine-moi/2026-07-20-interface-web-sircom-2026.md`.
- Décision d'architecture cible : FastAPI, Swagger/OpenAPI, frontend DSFR, exécution locale Mac Alex puis VPS interne.
- Décision de traitement 2026 : Excel multi-onglets, fusion à plat par `id_dossier`, mapping semi-automatique avec profils, export CSV final strictement compatible avec le CSV InDesign 2025 de référence.
- Décision images 2026 : zip images en entrée, images à la racine, conversion JPG, dossier final `export-jpg-resize/`, absences non bloquantes avec alertes.
