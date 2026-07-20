# TODO

## Sircom 2026

- Créer un jeu Excel synthétique multi-onglets pour tester le pipeline avant réception du vrai fichier 2026.
  - Inclure des onglets multiples avec `id_dossier` comme clé commune.
  - Varier l'ordre des colonnes et la position de `id_dossier`.
  - Prévoir des colonnes région/département présentes, absentes ou mal nommées.
  - Couvrir cellules vides, colonnes entièrement vides, lignes sans `id_dossier`, formats sensibles et noms d'onglets longs.
  - Ajouter un diagnostic automatique à l'upload : structure détectée, onglets, colonnes, clé `id_dossier`, alertes et blocages.
