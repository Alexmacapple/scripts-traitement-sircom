# Revue RGAA 4.1.2 - 106 critères et tests associés

Date : 2026-07-24

Projet : `madeinfrance` / Sircom 2026

Source principale : référentiel AY11 local `rgaa-4.1.2.json`, lui-même basé sur le RGAA 4.1.2.

Échantillon Sircom passé dans AY11 : 8 pages rendues, dont accueil, pages légales, vue lot, workflow Excel, workflow images et workflow export.

## Statut de ce document

Ce document est une revue de couverture et de traçabilité, pas une déclaration officielle de conformité RGAA.

Il liste les 106 critères RGAA et leurs tests associés. Il indique aussi ce que le préaudit AY11 a pu collecter automatiquement sur Sircom. Les décisions finales `C`, `NC`, `NA` ou `NT` exigent une revue humaine critère par critère.

## Synthèse

- Référentiel : RGAA 4.1.2.
- Thèmes : 13.
- Critères : 106.
- Tests : 258.
- Profil AY11 : `rgaa-106`, exécutable en mode strict humain : `true`.
- Statut de collecte AY11 : `collected=11`, `pending_collection=95`.
- Preuves collectées automatiquement sur Sircom : 81 collections, 292 cibles observées.
- Signaux visibles AY11 : noms accessibles `0`, textes/liens `0`, formulaires sensibles `0`.
- Suspicion HTML statique AY11 : `0`.

## Lecture des statuts

- `collecté sans signal` : AY11 a collecté des preuves automatiques sur le critère dans l’échantillon Sircom et aucune suspicion n’est remontée dans la passe finale.
- `revue humaine requise` : le critère fait partie du RGAA complet, mais le collecteur automatique ne produit pas de décision exploitable sur notre échantillon.
- `tests associés` : identifiants officiels des tests RGAA rattachés au critère dans le référentiel AY11 local.

## Matrice par thème

### Thème 1 - Images

Critères du thème : 9.

#### Critère 1.1

Critère : Chaque [image porteuse d’information](#image-porteuse-d-information) a-t-elle une [alternative textuelle](#alternative-textuelle-image) ?

Tests associés (8) : `1.1.1`, `1.1.2`, `1.1.3`, `1.1.4`, `1.1.5`, `1.1.6`, `1.1.7`, `1.1.8`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `has_aria_labelledby`, `has_aria_label`, `has_alt`, `has_title`, `has_adjacent_link`, `has_adjacent_link_group`, `has_alternative_interface_component`, `has_role_img` ; +4 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.2

Critère : Chaque [image de décoration](#image-de-decoration) est-elle correctement ignorée par les technologies d’assistance ?

Tests associés (6) : `1.2.1`, `1.2.2`, `1.2.3`, `1.2.4`, `1.2.5`, `1.2.6`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +38 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.3

Critère : Pour chaque image [porteuse d’information](#image-porteuse-d-information) ayant une [alternative textuelle](#alternative-textuelle-image), cette alternative est-elle pertinente (hors cas particuliers) ?

Tests associés (9) : `1.3.1`, `1.3.2`, `1.3.3`, `1.3.4`, `1.3.5`, `1.3.6`, `1.3.7`, `1.3.8`, `1.3.9`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +46 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 1.4

Critère : Pour chaque image utilisée comme [CAPTCHA](#captcha) ou comme [image-test](#image-test), ayant une [alternative textuelle](#alternative-textuelle-image), cette alternative permet-elle d’identifier la nature et la fonction de l’image ?

Tests associés (7) : `1.4.1`, `1.4.2`, `1.4.3`, `1.4.4`, `1.4.5`, `1.4.6`, `1.4.7`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +45 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.5

Critère : Pour chaque image utilisée comme [CAPTCHA](#captcha), une solution d’accès alternatif au contenu ou à la fonction du CAPTCHA est-elle présente ?

Tests associés (2) : `1.5.1`, `1.5.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.6

Critère : Chaque image [porteuse d’information](#image-porteuse-d-information) a-t-elle, si nécessaire, une [description détaillée](#description-detaillee-image) ?

Tests associés (10) : `1.6.1`, `1.6.2`, `1.6.3`, `1.6.4`, `1.6.5`, `1.6.6`, `1.6.7`, `1.6.8`, `1.6.9`, `1.6.10`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +56 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.7

Critère : Pour chaque image [porteuse d’information](#image-porteuse-d-information) ayant une [description détaillée](#description-detaillee-image), cette description est-elle pertinente ?

Tests associés (6) : `1.7.1`, `1.7.2`, `1.7.3`, `1.7.4`, `1.7.5`, `1.7.6`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +21 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.8

Critère : Chaque [image texte](#image-texte) [porteuse d’information](#image-porteuse-d-information), en l’absence d’un [mécanisme de remplacement](#mecanisme-de-remplacement), doit si possible être remplacée par du [texte stylé](#texte-style). Cette règle est-elle respectée (hors cas particuliers) ?

Tests associés (6) : `1.8.1`, `1.8.2`, `1.8.3`, `1.8.4`, `1.8.5`, `1.8.6`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +28 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 1.9

Critère : Chaque [légende d’image](#legende-d-image) est-elle, si nécessaire, correctement reliée à l’image correspondante ?

Tests associés (5) : `1.9.1`, `1.9.2`, `1.9.3`, `1.9.4`, `1.9.5`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +16 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 2 - Cadres

Critères du thème : 2.

#### Critère 2.1

Critère : Chaque [cadre](#cadre) a-t-il un [titre de cadre](#titre-de-cadre) ?

Tests associés (1) : `2.1.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 2.2

Critère : Pour chaque [cadre](#cadre) ayant un [titre de cadre](#titre-de-cadre), ce titre de cadre est-il pertinent ?

Tests associés (1) : `2.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 3 - Couleurs

Critères du thème : 3.

#### Critère 3.1

Critère : Dans chaque page web, l’[information](#information-donnee-par-la-couleur) ne doit pas être donnée uniquement par la couleur. Cette règle est-elle respectée ?

Tests associés (6) : `3.1.1`, `3.1.2`, `3.1.3`, `3.1.4`, `3.1.5`, `3.1.6`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `css_couleur`, `candidat_canal_alternatif`, `mention_couleur_texte`, `cible_potentielle_proche`, `noeud_image`, `candidat_alternative_textuelle`, `candidat_canal_non_coloriel`, `capture_rendu_gris_ou_daltonisme` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 3.2

Critère : Dans chaque page web, le [contraste](#contraste) entre la couleur du texte et la couleur de son arrière-plan est-il suffisamment élevé (hors cas particuliers) ?

Tests associés (5) : `3.2.1`, `3.2.2`, `3.2.3`, `3.2.4`, `3.2.5`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +22 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 3.3

Critère : Dans chaque page web, les couleurs utilisées dans les [composants d’interface](#composant-d-interface) ou les éléments graphiques porteurs d’informations sont-elles suffisamment contrastées (hors cas particuliers) ?

Tests associés (4) : `3.3.1`, `3.3.2`, `3.3.3`, `3.3.4`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +27 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 4 - Multimédia

Critères du thème : 13.

#### Critère 4.1

Critère : Chaque [média temporel](#media-temporel-type-son-video-et-synchronise) pré-enregistré a-t-il, si nécessaire, une [transcription textuelle](#transcription-textuelle-media-temporel) ou une [audiodescription](#audiodescription-synchronisee-media-temporel) (hors cas particuliers) ?

Tests associés (3) : `4.1.1`, `4.1.2`, `4.1.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `noeud_media_temporel`, `type_media_candidat`, `media_prerecorde_candidat`, `transcription_lien_ou_bouton_adjacent`, `transcription_adjacente_identifiable`, `contenu_transcription_extrait`, `association_media_transcription`, `inspectability` ; +6 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.2

Critère : Pour chaque [média temporel](#media-temporel-type-son-video-et-synchronise) pré-enregistré ayant une [transcription textuelle](#transcription-textuelle-media-temporel) ou une [audiodescription](#audiodescription-synchronisee-media-temporel) synchronisée, celles-ci sont-elles pertinentes (hors cas particuliers) ?

Tests associés (3) : `4.2.1`, `4.2.2`, `4.2.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +15 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.3

Critère : Chaque [média temporel](#media-temporel-type-son-video-et-synchronise) synchronisé pré-enregistré a-t-il, si nécessaire, des [sous-titres synchronisés](#sous-titres-synchronises-objet-multimedia) (hors cas particuliers) ?

Tests associés (2) : `4.3.1`, `4.3.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +15 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.4

Critère : Pour chaque [média temporel](#media-temporel-type-son-video-et-synchronise) synchronisé pré-enregistré ayant des [sous-titres synchronisés](#sous-titres-synchronises-objet-multimedia), ces sous-titres sont-ils pertinents ?

Tests associés (1) : `4.4.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.5

Critère : Chaque [média temporel](#media-temporel-type-son-video-et-synchronise) pré-enregistré a-t-il, si nécessaire, une [audiodescription](#audiodescription-synchronisee-media-temporel) synchronisée (hors cas particuliers) ?

Tests associés (2) : `4.5.1`, `4.5.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.6

Critère : Pour chaque [média temporel](#media-temporel-type-son-video-et-synchronise) pré-enregistré ayant une [audiodescription](#audiodescription-synchronisee-media-temporel) synchronisée, celle-ci est-elle pertinente ?

Tests associés (2) : `4.6.1`, `4.6.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +14 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.7

Critère : Chaque [média temporel](#media-temporel-type-son-video-et-synchronise) est-il clairement identifiable (hors cas particuliers) ?

Tests associés (1) : `4.7.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.8

Critère : Chaque [média non temporel](#media-non-temporel) a-t-il, si nécessaire, une alternative (hors cas particuliers) ?

Tests associés (2) : `4.8.1`, `4.8.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.9

Critère : Pour chaque [média non temporel](#media-non-temporel) ayant une alternative, cette alternative est-elle pertinente ?

Tests associés (1) : `4.9.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.10

Critère : Chaque son déclenché automatiquement est-il [contrôlable](#controle-son-declenche-automatiquement) par l’utilisateur ?

Tests associés (1) : `4.10.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `observation_window`, `dom_media_inventory`, `html_media_runtime_evidence`, `audible_autoplay_candidate`, `js_play_calls`, `muted_or_silent_autoplay`, `duration_evidence`, `stop_control_candidate` ; +6 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.11

Critère : La consultation de chaque [média temporel](#media-temporel-type-son-video-et-synchronise) est-elle, si nécessaire, [contrôlable par le clavier et tout dispositif de pointage](#accessible-et-activable-par-le-clavier-et-tout-dispositif-de-pointage) ?

Tests associés (3) : `4.11.1`, `4.11.2`, `4.11.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +21 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.12

Critère : La consultation de chaque [média non temporel](#media-non-temporel) est-elle [contrôlable par le clavier et tout dispositif de pointage](#accessible-et-activable-par-le-clavier-et-tout-dispositif-de-pointage) ?

Tests associés (2) : `4.12.1`, `4.12.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +12 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 4.13

Critère : Chaque [média temporel](#media-temporel-type-son-video-et-synchronise) et [non temporel](#media-non-temporel) est-il [compatible avec les technologies d’assistance](#compatible-avec-les-technologies-d-assistance) (hors cas particuliers) ?

Tests associés (2) : `4.13.1`, `4.13.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 5 - Tableaux

Critères du thème : 8.

#### Critère 5.1

Critère : Chaque [tableau de données complexe](#tableau-de-donnees-complexe) a-t-il un [résumé](#resume-de-tableau) ?

Tests associés (1) : `5.1.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 5.2

Critère : Pour chaque [tableau de données complexe](#tableau-de-donnees-complexe) ayant un [résumé](#resume-de-tableau), celui-ci est-il pertinent ?

Tests associés (1) : `5.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 5.3

Critère : Pour chaque [tableau de mise en forme](#tableau-de-mise-en-forme), le contenu linéarisé reste-t-il compréhensible ?

Tests associés (1) : `5.3.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `table_count`, `table_nodes`, `scope`, `inspection_limits`, `layout_table_candidate`, `data_table_semantics_candidate`, `has_role_presentation`, `role_none_candidate` ; +4 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 5.4

Critère : Pour chaque [tableau de données ayant un titre](#tableau-de-donnees-ayant-un-titre), le titre est-il correctement associé au tableau de données ?

Tests associés (1) : `5.4.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 5.5

Critère : Pour chaque [tableau de données ayant un titre](#tableau-de-donnees-ayant-un-titre), celui-ci est-il pertinent ?

Tests associés (1) : `5.5.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 5.6

Critère : Pour chaque [tableau de données](#tableau-de-donnees), chaque [en-tête de colonne](#en-tete-de-colonne-ou-de-ligne) et chaque [en-tête de ligne](#en-tete-de-colonne-ou-de-ligne) sont-ils correctement déclarés ?

Tests associés (4) : `5.6.1`, `5.6.2`, `5.6.3`, `5.6.4`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 5.7

Critère : Pour chaque [tableau de données](#tableau-de-donnees), la technique appropriée permettant d’associer chaque cellule avec ses [en-têtes](#en-tete-de-colonne-ou-de-ligne) est-elle utilisée (hors cas particuliers) ?

Tests associés (5) : `5.7.1`, `5.7.2`, `5.7.3`, `5.7.4`, `5.7.5`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `table_count`, `data_table_candidate_count`, `table_nodes`, `scope`, `inspection_limits`, `html_table_structure`, `layout_table_exclusion_candidate`, `aria_table_role_candidate` ; +26 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 5.8

Critère : Chaque [tableau de mise en forme](#tableau-de-mise-en-forme) ne doit pas utiliser d’éléments propres aux  [tableaux de données](#tableau-de-donnees). Cette règle est-elle respectée ?

Tests associés (1) : `5.8.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +15 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 6 - Liens

Critères du thème : 2.

#### Critère 6.1

Critère : Chaque [lien](#lien) est-il explicite (hors cas particuliers) ?

Tests associés (5) : `6.1.1`, `6.1.2`, `6.1.3`, `6.1.4`, `6.1.5`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `link_count`, `link_nodes`, `link_type`, `visible_text`, `accessible_name`, `accessible_name_source`, `href_raw`, `href_normalise` ; +44 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 6.2

Critère : Dans chaque page web, chaque [lien](#lien) a-t-il un [intitulé](#intitule-ou-nom-accessible-de-lien) ?

Tests associés (1) : `6.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `link_count`, `link_nodes`, `link_selector`, `html_anchor_href_candidate`, `aria_role_link_candidate`, `scripted_navigation_candidate`, `svg_link_candidate`, `svg_xlink_href_candidate` ; +25 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 7 - Scripts

Critères du thème : 5.

#### Critère 7.1

Critère : Chaque [script](#script) est-il, si nécessaire, [compatible avec les technologies d’assistance](#compatible-avec-les-technologies-d-assistance) ?

Tests associés (3) : `7.1.1`, `7.1.2`, `7.1.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `script_component_count`, `component_nodes`, `component_type`, `js_controlled_component_candidate`, `native_interactive_element`, `custom_interactive_element`, `event_handler_candidate`, `computed_role` ; +56 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 7.2

Critère : Pour chaque [script](#script) ayant une [alternative](#alternative-a-script), cette alternative est-elle pertinente ?

Tests associés (2) : `7.2.1`, `7.2.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +10 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 7.3

Critère : Chaque [script](#script) est-il [contrôlable par le clavier et par tout dispositif de pointage](#accessible-et-activable-par-le-clavier-et-tout-dispositif-de-pointage) (hors cas particuliers) ?

Tests associés (2) : `7.3.1`, `7.3.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `script_event_handler_count`, `event_handler_nodes`, `dom_selector`, `html_excerpt`, `event_types_detected`, `inline_event_handler_candidate`, `add_event_listener_candidate`, `component_type` ; +60 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 7.4

Critère : Pour chaque [script](#script) qui initie un [changement de contexte](#changement-de-contexte), l’utilisateur est-il averti ou en a-t-il le contrôle ?

Tests associés (1) : `7.4.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 7.5

Critère : Dans chaque page web, les [messages de statut](#message-de-statut) sont-ils correctement restitués par les technologies d’assistance ?

Tests associés (3) : `7.5.1`, `7.5.2`, `7.5.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +16 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 8 - Éléments obligatoires

Critères du thème : 10.

#### Critère 8.1

Critère : Chaque page web est-elle définie par un [type de document](#type-de-document) ?

Tests associés (3) : `8.1.1`, `8.1.2`, `8.1.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 8.2

Critère : Pour chaque page web, le code source généré est-il valide selon le [type de document](#type-de-document) spécifié ?

Tests associés (1) : `8.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 8.3

Critère : Dans chaque page web, la [langue par défaut](#langue-par-defaut) est-elle présente ?

Tests associés (1) : `8.3.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `html_element_present`, `document_markup_flavour`, `html_lang_present`, `html_lang_value`, `html_lang_source`, `html_xml_lang_present`, `html_xml_lang_value`, `html_xml_lang_source` ; +12 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 8.4

Critère : Pour chaque page web ayant une [langue par défaut](#langue-par-defaut), le [code de langue](#code-de-langue) est-il pertinent ?

Tests associés (1) : `8.4.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `default_language_source`, `document_markup_flavour`, `html_lang_value`, `html_xml_lang_value`, `default_language_code_raw`, `default_language_code_normalized`, `language_code_primary_subtag`, `language_code_option` ; +35 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 8.5

Critère : Chaque page web a-t-elle un [titre de page](#titre-de-page) ?

Tests associés (1) : `8.5.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `html_document_candidate`, `head_element_present`, `title_element_present`, `title_element_in_head`, `title_count`, `title_nodes`, `title_text`, `title_text_trimmed` ; +25 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 8.6

Critère : Pour chaque page web ayant un [titre de page](#titre-de-page), ce titre est-il pertinent ?

Tests associés (1) : `8.6.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 8.7

Critère : Dans chaque page web, chaque [changement de langue](#changement-de-langue) est-il indiqué dans le code source (hors cas particuliers) ?

Tests associés (1) : `8.7.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 8.8

Critère : Dans chaque page web, le code de langue de chaque [changement de langue](#changement-de-langue) est-il valide et pertinent ?

Tests associés (1) : `8.8.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 8.9

Critère : Dans chaque page web, les balises ne doivent pas être utilisées [uniquement à des fins de présentation](#uniquement-a-des-fins-de-presentation). Cette règle est-elle respectée ?

Tests associés (1) : `8.9.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +12 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 8.10

Critère : Dans chaque page web, les changements du [sens de lecture](#sens-de-lecture) sont-ils signalés ?

Tests associés (2) : `8.10.1`, `8.10.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +9 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 9 - Structuration de l’information

Critères du thème : 4.

#### Critère 9.1

Critère : Dans chaque page web, l’information est-elle structurée par l’utilisation appropriée de [titres](#titre) ?

Tests associés (3) : `9.1.1`, `9.1.2`, `9.1.3`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `heading_count`, `native_heading_count`, `aria_heading_count`, `h1_count`, `heading_nodes`, `heading_dom_order`, `heading_levels_sequence`, `heading_level_distribution` ; +49 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 9.2

Critère : Dans chaque page web, la [structure du document](#structure-du-document) est-elle cohérente (hors cas particuliers) ?

Tests associés (1) : `9.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 9.3

Critère : Dans chaque page web, chaque [liste](#listes) est-elle correctement structurée ?

Tests associés (3) : `9.3.1`, `9.3.2`, `9.3.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +19 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 9.4

Critère : Dans chaque page web, chaque citation est-elle correctement indiquée ?

Tests associés (2) : `9.4.1`, `9.4.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 10 - Présentation de l’information

Critères du thème : 14.

#### Critère 10.1

Critère : Dans le site web, des [feuilles de styles](#feuille-de-style) sont-elles utilisées pour contrôler la [présentation de l’information](#presentation-de-l-information) ?

Tests associés (3) : `10.1.1`, `10.1.2`, `10.1.3`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +23 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 10.2

Critère : Dans chaque page web, le [contenu visible](#contenu-visible) porteur d’information reste-t-il présent lorsque les [feuilles de styles](#feuille-de-style) sont désactivées ?

Tests associés (1) : `10.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.3

Critère : Dans chaque page web, l’information reste-t-elle [compréhensible](#comprehensible-ordre-de-lecture) lorsque les [feuilles de styles](#feuille-de-style) sont désactivées ?

Tests associés (1) : `10.3.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `html_document_candidate`, `stylesheet_link_nodes`, `style_element_nodes`, `inline_style_attribute_nodes`, `author_css_disable_strategy`, `css_disabled_state_confirmed`, `screenshot_css_on`, `screenshot_css_off` ; +38 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.4

Critère : Dans chaque page web, le texte reste-t-il lisible lorsque la [taille des caractères](#taille-des-caracteres) est augmentée jusqu’à 200 %, au moins (hors cas particuliers) ?

Tests associés (2) : `10.4.1`, `10.4.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +16 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.5

Critère : Dans chaque page web, les déclarations CSS de couleurs de fond d’élément et de police sont-elles correctement utilisées ?

Tests associés (3) : `10.5.1`, `10.5.2`, `10.5.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +16 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.6

Critère : Dans chaque page web, chaque [lien dont la nature n’est pas évidente](#lien-dont-la-nature-n-est-pas-evidente) est-il visible par rapport au texte environnant ?

Tests associés (1) : `10.6.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `link_count`, `link_nodes`, `text_link_candidate_count`, `text_link_nodes`, `html_anchor_href_candidate`, `aria_role_link_candidate`, `link_text_only_content`, `image_link_exclusion_candidate` ; +59 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.7

Critère : Dans chaque page web, pour chaque élément recevant le focus, la [prise de focus](#prise-de-focus) est-elle visible ?

Tests associés (1) : `10.7.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `focusable_element_count`, `focusable_nodes`, `native_focusable_candidate`, `html_anchor_href_candidate`, `button_focusable_candidate`, `form_control_focusable_candidate`, `summary_focusable_candidate`, `iframe_focusable_candidate` ; +60 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.8

Critère : Pour chaque page web, les [contenus cachés](#contenu-cache) ont-ils vocation à être ignorés par les technologies d’assistance ?

Tests associés (1) : `10.8.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +13 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.9

Critère : Dans chaque page web, l’information ne doit pas être donnée uniquement [par la forme, taille ou position](#indication-donnee-par-la-forme-la-taille-ou-la-position). Cette règle est-elle respectée ?

Tests associés (4) : `10.9.1`, `10.9.2`, `10.9.3`, `10.9.4`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +28 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.10

Critère : Dans chaque page web, l’information ne doit pas être donnée [par la forme, taille ou position](#indication-donnee-par-la-forme-la-taille-ou-la-position) uniquement. Cette règle est-elle implémentée de façon pertinente ?

Tests associés (4) : `10.10.1`, `10.10.2`, `10.10.3`, `10.10.4`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +14 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.11

Critère : Pour chaque page web, les contenus peuvent-ils être présentés sans perte d’information ou de fonctionnalité et sans avoir recours soit à un défilement vertical pour une fenêtre ayant une hauteur de 256 px, soit à un défilement horizontal pour une fenêtre ayant une largeur de 320 px (hors cas particuliers) ?

Tests associés (2) : `10.11.1`, `10.11.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +14 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.12

Critère : Dans chaque page web, les propriétés d’espacement du texte peuvent-elles être redéfinies par l’utilisateur sans perte de contenu ou de fonctionnalité (hors cas particuliers) ?

Tests associés (1) : `10.12.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.13

Critère : Dans chaque page web, les contenus additionnels apparaissant à la prise de focus ou au survol d’un [composant d’interface](#composant-d-interface) sont-ils contrôlables par l’utilisateur (hors cas particuliers) ?

Tests associés (3) : `10.13.1`, `10.13.2`, `10.13.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +22 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 10.14

Critère : Dans chaque page web, les contenus additionnels apparaissant via les styles CSS uniquement peuvent-ils être rendus visibles au clavier et par tout dispositif de pointage ?

Tests associés (2) : `10.14.1`, `10.14.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +13 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 11 - Formulaires

Critères du thème : 13.

#### Critère 11.1

Critère : Chaque [champ de formulaire](#champ-de-saisie-de-formulaire) a-t-il une [étiquette](#etiquette-de-champ-de-formulaire) ?

Tests associés (3) : `11.1.1`, `11.1.2`, `11.1.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_field_count`, `form_field_nodes`, `field_tag_name`, `input_type`, `aria_role`, `field_id`, `field_name_attribute`, `field_disabled_or_hidden_candidate` ; +58 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.2

Critère : Chaque [étiquette](#etiquette-de-champ-de-formulaire) associée à un [champ de formulaire](#champ-de-saisie-de-formulaire) est-elle pertinente (hors cas particuliers) ?

Tests associés (6) : `11.2.1`, `11.2.2`, `11.2.3`, `11.2.4`, `11.2.5`, `11.2.6`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_field_count`, `form_field_nodes`, `field_tag_name`, `input_type`, `aria_role`, `field_id`, `field_name_attribute`, `field_purpose_candidate` ; +61 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.3

Critère : Dans chaque [formulaire](#formulaire), chaque [étiquette](#etiquette-de-champ-de-formulaire) associée à un [champ de formulaire](#champ-de-saisie-de-formulaire) ayant la même fonction et répétée plusieurs fois dans une même page ou dans un [ensemble de pages](#ensemble-de-pages) est-elle [cohérente](#etiquettes-coherentes) ?

Tests associés (2) : `11.3.1`, `11.3.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +12 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.4

Critère : Dans chaque [formulaire](#formulaire), chaque [étiquette de champ](#etiquette-de-champ-de-formulaire) et son champ associé sont-ils [accolés](#accoles-etiquette-et-champ-accoles) (hors cas particuliers) ?

Tests associés (3) : `11.4.1`, `11.4.2`, `11.4.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +21 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.5

Critère : Dans chaque [formulaire](#formulaire), les [champs de même nature](#champs-de-meme-nature) sont-ils regroupés, si nécessaire ?

Tests associés (1) : `11.5.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_count`, `form_field_count`, `form_field_nodes`, `field_tag_name`, `input_type`, `aria_role`, `field_name_attribute`, `field_id` ; +37 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.6

Critère : Dans chaque [formulaire](#formulaire), chaque regroupement de [champs de même nature](#champs-de-meme-nature) a-t-il une [légende](#legende) ?

Tests associés (1) : `11.6.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_count`, `form_field_count`, `form_field_nodes`, `field_tag_name`, `input_type`, `aria_role`, `field_name_attribute`, `field_id` ; +47 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.7

Critère : Dans chaque [formulaire](#formulaire), chaque [légende](#legende) associée à un regroupement de [champs de même nature](#champs-de-meme-nature) est-elle pertinente ?

Tests associés (1) : `11.7.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.8

Critère : Dans chaque [formulaire](#formulaire), les [items de même nature d’une liste de choix](#items-de-meme-nature-d-une-liste-de-choix) sont-ils regroupés de manière pertinente ?

Tests associés (3) : `11.8.1`, `11.8.2`, `11.8.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +20 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.9

Critère : Dans chaque [formulaire](#formulaire), l’intitulé de chaque [bouton](#bouton-formulaire) est-il pertinent (hors cas particuliers) ?

Tests associés (2) : `11.9.1`, `11.9.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_count`, `button_count`, `button_nodes`, `button_tag_name`, `button_input_type`, `native_button_candidate`, `button_element_candidate`, `input_submit_candidate` ; +57 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.10

Critère : Dans chaque [formulaire](#formulaire), le [contrôle de saisie](#controle-de-saisie-formulaire) est-il utilisé de manière pertinente (hors cas particuliers) ?

Tests associés (7) : `11.10.1`, `11.10.2`, `11.10.3`, `11.10.4`, `11.10.5`, `11.10.6`, `11.10.7`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `form_count`, `form_nodes`, `form_field_count`, `form_field_nodes`, `input_type_search_candidate`, `search_field_clean_non_applicable_candidate`, `single_field_form_candidate`, `optional_fields_visible_indication_candidate` ; +81 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.11

Critère : Dans chaque [formulaire](#formulaire), le [contrôle de saisie](#controle-de-saisie-formulaire) est-il accompagné, si nécessaire, de suggestions facilitant la correction des erreurs de saisie ?

Tests associés (2) : `11.11.1`, `11.11.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +11 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.12

Critère : Pour chaque [formulaire](#formulaire) ayant pour effet la modification ou la suppression de données, ou transmettant des réponses à un test ou à un examen, ou dont la validation a des conséquences financières ou juridiques, les données saisies peuvent-elles être modifiées, mises à jour ou récupérées par l’utilisateur ?

Tests associés (2) : `11.12.1`, `11.12.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 11.13

Critère : La finalité d’un champ de saisie peut-elle être déduite pour faciliter le remplissage automatique des champs avec les données de l’utilisateur ?

Tests associés (1) : `11.13.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 12 - Navigation

Critères du thème : 11.

#### Critère 12.1

Critère : Chaque [ensemble de pages](#ensemble-de-pages) dispose-t-il de deux [systèmes de navigation](#systeme-de-navigation) différents, au moins (hors cas particuliers) ?

Tests associés (1) : `12.1.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.2

Critère : Dans chaque [ensemble de pages](#ensemble-de-pages), le [menu et les barres de navigation](#menu-et-barre-de-navigation) sont-ils toujours à la même place (hors cas particuliers) ?

Tests associés (1) : `12.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.3

Critère : La [page « plan du site »](#page-plan-du-site) est-elle pertinente ?

Tests associés (3) : `12.3.1`, `12.3.2`, `12.3.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +19 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.4

Critère : Dans chaque [ensemble de pages](#ensemble-de-pages), la [page « plan du site »](#page-plan-du-site) est-elle accessible à partir d’une fonctionnalité identique ?

Tests associés (3) : `12.4.1`, `12.4.2`, `12.4.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.5

Critère : Dans chaque [ensemble de pages](#ensemble-de-pages), le [moteur de recherche](#moteur-de-recherche-interne-a-un-site-web) est-il atteignable de manière identique ?

Tests associés (3) : `12.5.1`, `12.5.2`, `12.5.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.6

Critère : Les zones de regroupement de contenus présentes dans plusieurs pages web (zones d’[en-tête](#zone-d-en-tete), de [navigation principale](#menu-et-barre-de-navigation), de [contenu principal](#zone-de-contenu-principal), de [pied de page](#zone-de-pied-de-page) et de [moteur de recherche](#moteur-de-recherche-interne-a-un-site-web)) peuvent-elles être atteintes ou évitées ?

Tests associés (1) : `12.6.1`.

Statut AY11 Sircom : `collecté sans signal`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Décision RGAA finale à confirmer humainement, mais aucune suspicion automatique n’a été observée sur l’échantillon.

#### Critère 12.7

Critère : Dans chaque page web, un [lien d’évitement ou d’accès rapide](#liens-d-evitement-ou-d-acces-rapide) à la [zone de contenu principal](#zone-de-contenu-principal) est-il présent (hors cas particuliers) ?

Tests associés (2) : `12.7.1`, `12.7.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.8

Critère : Dans chaque page web, l’[ordre de tabulation](#ordre-de-tabulation) est-il [cohérent](#comprehensible-ordre-de-lecture) ?

Tests associés (2) : `12.8.1`, `12.8.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `focusable_count`, `focusable_nodes`, `focusable_dom_order`, `focusable_accessible_name`, `focusable_role`, `native_focusable_candidate`, `html_anchor_href_candidate`, `button_focusable_candidate` ; +70 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.9

Critère : Dans chaque page web, la navigation ne doit pas contenir de piège au clavier. Cette règle est-elle respectée ?

Tests associés (1) : `12.9.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `focusable_count`, `focusable_nodes`, `focusable_role`, `focusable_accessible_name`, `focusable_source`, `tab_sequence_forward`, `tab_sequence_backward`, `active_element_trace` ; +42 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.10

Critère : Dans chaque page web, les [raccourcis clavier](#raccourci-clavier) n’utilisant qu’une seule touche (lettre minuscule ou majuscule, ponctuation, chiffre ou symbole) sont-ils contrôlables par l’utilisateur ?

Tests associés (1) : `12.10.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 12.11

Critère : Dans chaque page web, les contenus additionnels apparaissant au survol, à la prise de focus ou à l’activation d’un [composant d’interface](#composant-d-interface) sont-ils si nécessaire atteignables au clavier ?

Tests associés (1) : `12.11.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

### Thème 13 - Consultation

Critères du thème : 12.

#### Critère 13.1

Critère : Pour chaque page web, l’utilisateur a-t-il le contrôle de chaque limite de temps modifiant le contenu (hors cas particuliers) ?

Tests associés (4) : `13.1.1`, `13.1.2`, `13.1.3`, `13.1.4`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +17 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.2

Critère : Dans chaque page web, l’ouverture d’une nouvelle fenêtre ne doit pas être déclenchée sans action de l’utilisateur. Cette règle est-elle respectée ?

Tests associés (1) : `13.2.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.3

Critère : Dans chaque page web, chaque document bureautique en téléchargement possède-t-il, si nécessaire, une [version accessible](#version-accessible-pour-un-document-en-telechargement) (hors cas particuliers) ?

Tests associés (1) : `13.3.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +10 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.4

Critère : Pour chaque document bureautique ayant une [version accessible](#version-accessible-pour-un-document-en-telechargement), cette version offre-t-elle la même information ?

Tests associés (1) : `13.4.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.5

Critère : Dans chaque page web, chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique) a-t-il une alternative ?

Tests associés (1) : `13.5.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.6

Critère : Dans chaque page web, pour chaque contenu cryptique (art ASCII, émoticône, syntaxe cryptique) ayant une alternative, cette alternative est-elle pertinente ?

Tests associés (1) : `13.6.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +7 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.7

Critère : Dans chaque page web, [les changements brusques de luminosité ou les effets de flash](#changement-brusque-de-luminosite-ou-effet-de-flash) sont-ils correctement utilisés ?

Tests associés (3) : `13.7.1`, `13.7.2`, `13.7.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +10 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.8

Critère : Dans chaque page web, chaque contenu en mouvement ou clignotant est-il [contrôlable](#controle-contenu-en-mouvement-ou-clignotant) par l’utilisateur ?

Tests associés (2) : `13.8.1`, `13.8.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +9 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.9

Critère : Dans chaque page web, le contenu proposé est-il consultable quelle que soit l’orientation de l’écran (portrait ou paysage) (hors cas particuliers) ?

Tests associés (1) : `13.9.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.10

Critère : Dans chaque page web, les fonctionnalités utilisables ou disponibles au moyen d’un [geste complexe](#gestes-complexes-et-gestes-simples) peuvent-elles être également disponibles au moyen d’un [geste simple](#gestes-complexes-et-gestes-simples) (hors cas particuliers) ?

Tests associés (2) : `13.10.1`, `13.10.2`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +18 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.11

Critère : Dans chaque page web, les actions déclenchées au moyen d’un dispositif de pointage sur un point unique de l’écran peuvent-elles faire l’objet d’une annulation (hors cas particuliers) ?

Tests associés (1) : `13.11.1`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +8 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

#### Critère 13.12

Critère : Dans chaque page web, les fonctionnalités qui impliquent un mouvement de l’appareil ou vers l’appareil peuvent-elles être satisfaites de manière alternative (hors cas particuliers) ?

Tests associés (3) : `13.12.1`, `13.12.2`, `13.12.3`.

Statut AY11 Sircom : `revue humaine requise`.

Preuves AY11 : `test_id`, `source_rgaa_locale`, `target_count`, `target_nodes`, `scope`, `inspectability`, `inspection_limits`, `human_review_question` ; +19 autres codes.

Revue restante : Aucune décision automatique de conformité ne doit être déduite ; tester manuellement l’applicabilité, les cas particuliers et le rendu réel.

## Conclusion opérationnelle

La revue confirme que les 106 critères et 258 tests du profil RGAA complet sont bien identifiés et traçables. Sur Sircom, AY11 a collecté automatiquement 11 critères sans signal final, mais 95 critères restent en revue humaine requise.

Donc la position de production reste inchangée : GO pour une production pilote sur le périmètre métier testé, mais pas de déclaration RGAA 100 % sans audit humain complet.
