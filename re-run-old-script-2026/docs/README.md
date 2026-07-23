---
type: Concept
title: "Documentation PDD OKF de la voie scriptée Sircom 2026"
description: "Index progressif des règles, de l'architecture et des preuves de la voie scriptée Sircom 2026."
tags: [pdd, okf, sircom-2026, scripts]
timestamp: "2026-07-23"
sources:
  - "../variables.md"
  - "../run_jeu_test_2026.py"
  - "../sircom2026_rules.py"
  - "../livrables_output_2026-07-24/run-2026-summary.json"
---

# Documentation PDD OKF

## Lire selon le besoin

Cette documentation applique le principe de divulgation progressive : partir du
contrat métier, descendre vers l'architecture seulement si nécessaire, puis lire
les preuves quand il faut valider ou rejouer.

## Parcours recommandé

1. [Variables de run](../variables.md) : quoi modifier pour rejouer.
2. [Spécification fonctionnelle](specification-fonctionnelle.md) : quoi produire
   et quelles règles métier respecter.
3. [Spécification technique](specification-technique.md) : comment les scripts
   enchaînent les transformations.
4. [Vérification script par script](verification-scripts-2026.md) : ce qui a été
   contrôlé et ce qui reste à surveiller.

## Contrat de lecture

- Une page porte un concept principal.
- Les sources locales sont indiquées dans le frontmatter OKF.
- Les livrables courants sont datés avec le suffixe ISO court
  `YYYY-MM-DD`.
- Les preuves valent pour le jeu de test du 23 juillet 2026 et le dernier
  dossier de run contrôlé `livrables_output_2026-07-24/`.
