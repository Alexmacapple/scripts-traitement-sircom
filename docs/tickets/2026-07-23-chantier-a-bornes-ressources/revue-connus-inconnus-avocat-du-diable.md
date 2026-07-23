# Revue connu-inconnu et avocat du diable - chantier A

Date : 2026-07-23

Cible relue : la spec
`docs/specs/2026-07-23-chantier-a-bornes-ressources-sircom-2026.md` et les cinq
tickets du dossier `docs/tickets/2026-07-23-chantier-a-bornes-ressources/`.

## Analyse connu-inconnu

Reformulation : le chantier A transforme le diagnostic convergent des deux
revues de code en tickets prêts à implémenter. Le but est de fermer le risque de
saturation locale sans lancer de refactor large.

### Ancrage - connus connus

- `[^]` Le risque prioritaire est confirmé par deux revues indépendantes :
  Excel/images/disque peuvent saturer avant ou pendant les traitements lourds.
- `[^]` Le dépôt a déjà des seams utiles : `Settings`, `public_limits()`,
  validation upload Excel, inspection zip images, matching images, readiness
  disque, worker et problèmes structurés.
- `[~]` Le tracker local fonctionne par fichiers Markdown, pas par issues
  GitHub.
- `[~]` Les tickets respectent la frontier : 01 et 04 peuvent démarrer, 02/03
  dépendent des limites, 05 ferme la preuve globale.

### Brouillard - connus inconnus

- `[^]` Calibrage image réel : les seuils doivent éviter de rejeter des photos
  Sircom légitimes. Décision : valeurs V1 hautes mais cohérentes avec Pillow,
  puis recalibrage si corpus réel disponible.
- `[^]` Point exact de refus Excel : certaines dimensions sont détectables à
  l'upload, d'autres seulement pendant le diagnostic borné. Décision : accepter
  les deux chemins mais exiger un résultat structuré dans chaque cas.
- `[~]` Politique disque : le seuil existant est un contrôle best-effort, pas une
  réservation. Décision : bloquer proprement le job et rendre le retry évident.
- `[~]` Preuve adversariale : construire de vrais fichiers énormes serait une
  mauvaise preuve. Décision : abaisser les seuils en test.

### Déni - inconnus connus

- `[^]` Hypothèse masquée : "tests adversariaux" peut être interprété comme la
  création de vrais fichiers lourds. Impact : tests lents, instables ou
  dangereux sur poste local.
- `[^]` Hypothèse masquée : `Image.MAX_IMAGE_PIXELS` et la limite applicative
  seront naturellement cohérents. Impact : deux politiques peuvent diverger et
  produire des refus différents selon l'environnement.
- `[~]` Hypothèse masquée : ajouter `ruff check` en CI est bloqué par les bornes
  ressources. Impact : petit gain CI retardé, mais acceptable si le ticket 05
  reste un ticket de consolidation.
- `[~]` Hypothèse masquée : un problème disque est un échec technique. Impact :
  mauvais statut, mauvaise action utilisateur, retry moins clair.

### Abîme - inconnus inconnus

- `[^]` Une limite trop stricte pourrait être découverte seulement sur un vrai
  corpus Sircom, avec des photos professionnelles très grandes mais légitimes.
  Signe précurseur : plusieurs images refusées alors qu'elles s'ouvrent
  correctement et dépassent seulement légèrement le seuil.
- `[~]` Les bornes peuvent être implémentées en doublonnant les règles entre
  upload, diagnostic, inspection et matching. Signe précurseur : codes d'erreur
  proches mais non identiques, tests divergents.
- `[~]` La vérification disque peut passer puis l'écriture échouer quand même.
  Signe précurseur : artefacts temporaires présents malgré problème disque.

### Risques prioritaires

1. Tests adversariaux trop lourds au lieu de seuils abaissés.
2. Ambiguïté du point propriétaire de refus Excel/images.
3. Divergence entre `SIRCOM_MAX_IMAGE_PIXELS` et Pillow.
4. Statut disque mal classé en échec technique non actionnable.

### Verdict connu-inconnu

Prêt sous conditions. Les tickets sont bons, mais ils devaient nommer plus
explicitement les points de refus, la cohérence Pillow et la stratégie de tests
adversariaux légers. Corrections appliquées dans cette passe.

## Avocat du diable

### Steel-man

Le découpage est raisonnable : il attaque le seul risque runtime prioritaire
identifié par deux revues, sans mélanger refactor, doc et exposition VPS. La
frontier est exploitable : configuration et garde disque peuvent partir en
parallèle, puis Excel/images, puis preuve CI. Les tickets citent les points
d'observation locaux au lieu d'imposer une nouvelle architecture.

### Préoccupations classées

1. Tests adversariaux qui deviennent eux-mêmes coûteux.
   Sévérité : Haute. Statut : bloquante avant implémentation.
   Cadre : inversion, modes de défaillance.
   Description : demander un Excel ou une image hors limites peut inciter un
   contributeur à générer des fichiers réellement énormes.
   Conséquence : tests lents, fragiles, voire saturation pendant la preuve du
   garde-fou.
   Recommandation : abaisser les seuils de configuration en test et construire
   de petits fichiers synthétiques. Correction ajoutée aux tickets 02, 03 et 05.

2. Propriété du refus Excel insuffisamment nette.
   Sévérité : Moyenne. Statut : bloquante avant ticket 02.
   Cadre : socratique clarification, modes de défaillance.
   Description : le ticket pouvait être lu comme "tout doit retourner 422 à
   l'upload", alors que certains dépassements seront plus sûrement détectés dans
   le diagnostic borné.
   Conséquence : risque de remettre du travail lourd dans la requête HTTP ou de
   produire une API incohérente.
   Recommandation : distinguer refus upload 422 si détectable sans scan complet,
   et blocage diagnostic avec problème structuré sinon. Correction ajoutée au
   ticket 02.

3. Propriété du refus image trop ouverte.
   Sévérité : Moyenne. Statut : bloquante avant ticket 03.
   Cadre : modes de défaillance, cohérence architecturale.
   Description : "inspection ou matching" laisse deux implémentations possibles
   et peut repousser le refus trop tard, au moment de la conversion.
   Conséquence : duplication des règles ou conversion non bornée malgré le
   ticket.
   Recommandation : faire de l'inspection zip le point propriétaire, puis
   revalider défensivement au matching. Correction ajoutée au ticket 03.

4. Divergence possible entre limite applicative et Pillow.
   Sévérité : Moyenne. Statut : à surveiller.
   Cadre : écarts d'environnement, cohérence d'exécution.
   Description : Pillow a sa propre protection anti-bomb ; si la limite
   applicative est plus permissive, égale ou modifiée globalement sans isolation,
   le comportement peut changer selon test, poste ou version.
   Conséquence : erreurs différentes pour le même fichier, tests instables ou
   refus non maîtrisé.
   Recommandation : définir une limite V1 cohérente avec Pillow, ne pas
   désactiver la protection, isoler tout changement global en test. Correction
   ajoutée à la spec et aux tickets 01/03.

5. Statut disque potentiellement mal classé.
   Sévérité : Basse. Statut : à surveiller.
   Cadre : questionnement perspective utilisateur.
   Description : disque insuffisant n'est pas une erreur applicative
   irréversible ; c'est une action opérationnelle attendue.
   Conséquence : si le job finit en échec technique, l'utilisateur ne saura pas
   s'il doit libérer de l'espace ou relancer.
   Recommandation : statut `bloque`, problème `bloquant`, détails free/required,
   pas de 500. Correction ajoutée au ticket 04.

6. Ruff check mélangé au ticket final.
   Sévérité : Basse. Statut : à surveiller.
   Cadre : chapeau bleu, priorisation.
   Description : le lint CI pourrait être livré immédiatement, mais il est
   regroupé dans le ticket 05 de preuve globale.
   Conséquence : petit gain CI retardé si les tickets 02/03/04 prennent du temps.
   Recommandation : acceptable tant que 05 reste le ticket de consolidation. Si
   l'équipe cherche une mini-frontier supplémentaire, extraire seulement cette
   ligne CI en ticket 00.

### Verdict avocat du diable

Livrer avec modifications appliquées. Le découpage reste bon ; les corrections
nécessaires portent sur la précision des critères, pas sur la stratégie. Frontier
inchangée : 01 et 04 maintenant, puis 02/03, puis 05.
