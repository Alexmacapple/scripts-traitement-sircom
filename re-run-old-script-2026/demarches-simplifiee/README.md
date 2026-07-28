# Kit Démarches simplifiées

Ce kit récupère les photos et les pièces jointes des dossiers de la procédure
`140205`.

Le processus a une seule étape manuelle obligatoire : coller un script dans la
console Chrome. Cette étape est nécessaire parce que l'accès aux dossiers
dépend de ta session Démarches simplifiées connectée.

L'orchestrateur choisit automatiquement le CSV Chrome le plus récent. Tu n'as
donc plus à chercher si Chrome l'a nommé `(1)`, `(2)` ou autrement.
Il refuse aussi les CSV plus anciens que le dernier script préparé, afin de ne
pas réutiliser silencieusement le résultat d'une précédente extraction.

## Prérequis

- Être connecté dans Chrome à `https://demarche.numerique.gouv.fr`.
- Avoir accès à la procédure `140205` avec ce compte.
- Mettre les numéros de dossiers dans `data/dossier-id.txt`, un numéro ou une
  URL de dossier par ligne.

Exemple de contenu :

```text
12345678
87654321
https://demarche.numerique.gouv.fr/procedures/140205/a-suivre/dossiers/23456789
```

Un modèle est disponible dans `data/dossier-id.example.txt`.

## Flux 1 : récupérer les images

### 1. Ouvrir le bon dossier dans le terminal

```bash
cd /Users/alex/Claude/projets-heberges/madeinfrance/re-run-old-script-2026/demarches-simplifiee
```

### 2. Vérifier la liste des dossiers

```bash
python3 orchestrator.py check-ids
```

Le résultat doit indiquer au moins un dossier. Pour le jeu courant :

```text
Dossiers trouvés: 6
Lignes ignorées: 0
```

Si `Lignes ignorées` est supérieur à zéro, corrige d'abord les lignes indiquées.

### 3. Préparer le script Chrome

```bash
python3 orchestrator.py prepare-photos --procedure-id 140205
open -a TextEdit results/run_extract_product_photos.js
```

### 4. Copier le script depuis TextEdit

Dans TextEdit :

1. clique dans le document ;
2. fais `Cmd + A` ;
3. fais `Cmd + C`.

Ne copie rien d'autre avant l'étape suivante.

### 5. Lancer l'extraction dans Chrome

1. Ouvre `https://demarche.numerique.gouv.fr/procedures/140205`.
2. Ouvre la console avec `Cmd + Option + J`.
3. Si Chrome bloque le collage, tape `allow pasting`, puis appuie sur Entrée.
4. Colle le script avec `Cmd + V`.
5. Appuie sur Entrée.
6. Attends l'affichage de `Synthèse photos produit`.

Exemple de fin normale :

```text
6/6 67890123
Synthèse photos produit {ok: 14}
```

Chrome télécharge deux CSV :

```text
photos-produits-dossiers.csv
photos-produits-dossiers-anomalies.csv
```

Le second contient uniquement les dossiers pour lesquels aucune image n'a été
trouvée.

### 6. Contrôler automatiquement le dernier CSV

Dans le terminal :

```bash
python3 orchestrator.py check-photos
```

Exemple de résultat valide :

```text
Lignes: 14
Dossiers distincts: 6
Lignes avec URL: 14
Images détectées: 14
Statuts:
- ok: 14
Validation: OK
```

Si le contrôle indique `aucune URL` ou `aucune image`, ne lance pas le
téléchargement. Passe à la section « Dossiers sans image » ci-dessous.

### 7. Télécharger les images

Lance cette commande rapidement, car les URLs Démarches simplifiées expirent :

```bash
python3 orchestrator.py download-photos
```

La commande choisit automatiquement le CSV photo le plus récent, y compris
s'il se termine par `(1)` ou `(2)`.

Exemple de résultat :

```text
Images détectées: 14
Dossiers couverts: 6
Pièces jointes à télécharger: 14
14/14 - téléchargées=14 déjà_présentes=0 erreurs=0
Erreurs: 0
```

Les images sont ici :

```text
~/Downloads/photos-produits-demarches-2027
```

Le rapport est ici :

```text
~/Downloads/rapport-photos-produits-2027.csv
```

### 8. Ouvrir le dossier des images

```bash
open "$HOME/Downloads/photos-produits-demarches-2027"
```

Une relance de `download-photos` est sûre : les fichiers déjà présents sont
signalés par `déjà_présentes` et ne sont pas téléchargés une seconde fois.

## Dossiers sans image

Le CSV `photos-produits-dossiers-anomalies.csv` sert à basculer uniquement les
dossiers sans image vers le flux des pièces jointes.

Prépare automatiquement le script à partir du CSV d'anomalies le plus récent :

```bash
python3 orchestrator.py prepare-complete-errors --procedure-id 140205
open -a TextEdit results/run_extract_complete_dossiers.js
```

Dans TextEdit, fais d'abord `Cmd + A`, puis `Cmd + C`. Continue ensuite au flux
2, à partir de l'étape 3.

Si la commande répond `Aucun dossier trouvé`, le CSV d'anomalies est vide :
aucune bascule n'est nécessaire.

## Flux 2 : récupérer les pièces jointes par dossier

Ce flux récupère toutes les pièces jointes et les range dans un sous-dossier
par numéro de dossier.

Attention : ce flux ne fabrique pas de fichier ZIP. Il produit des dossiers
classés. Chrome enregistre aussi le texte visible des dossiers dans
`dossiers-complets-textes.json`.

### 1. Choisir les dossiers

Pour traiter tous les numéros de `data/dossier-id.txt` :

```bash
python3 orchestrator.py prepare-complete --procedure-id 140205
```

Pour traiter seulement les dossiers sans image, utilise plutôt la commande de
la section précédente :

```bash
python3 orchestrator.py prepare-complete-errors --procedure-id 140205
```

### 2. Ouvrir et copier le script

```bash
open -a TextEdit results/run_extract_complete_dossiers.js
```

Dans TextEdit, fais `Cmd + A`, puis `Cmd + C`.

### 3. Lancer l'extraction dans Chrome

1. Ouvre `https://demarche.numerique.gouv.fr/procedures/140205`.
2. Ouvre la console avec `Cmd + Option + J`.
3. Colle le script avec `Cmd + V`.
4. Appuie sur Entrée.
5. Attends l'affichage de `Synthèse pièces jointes`.

Chrome télécharge :

```text
dossiers-complets-pieces-jointes.csv
dossiers-complets-textes.json
```

### 4. Contrôler automatiquement le dernier CSV

```bash
python3 orchestrator.py check-complete
```

`Lignes avec URL` doit être supérieur à zéro et la commande doit terminer par :

```text
Validation: OK
```

### 5. Télécharger et classer les pièces jointes

```bash
python3 orchestrator.py download-complete
```

La commande sélectionne le CSV le plus récent et range automatiquement les
fichiers par dossier :

```text
~/Downloads/dossiers-complets-pieces-jointes-2027/12345678/
~/Downloads/dossiers-complets-pieces-jointes-2027/87654321/
```

Le rapport est ici :

```text
~/Downloads/rapport-pj-dossiers-complets-2027.csv
```

### 6. Ouvrir les dossiers téléchargés

```bash
open "$HOME/Downloads/dossiers-complets-pieces-jointes-2027"
```

## Dépannage

### Chrome affiche `allow pasting`

Tape exactement :

```text
allow pasting
```

Appuie sur Entrée, puis recolle le script.

### Le terminal affiche `dquote>`

Un guillemet est resté ouvert. Appuie sur `Ctrl + C`, puis relance la commande
complète.

### Aucun CSV n'est trouvé

Le script Chrome n'a pas fini ou Chrome n'a pas autorisé le téléchargement.
Retourne dans la console Chrome, vérifie la synthèse, puis regarde les
téléchargements Chrome.

Il n'est pas nécessaire de renommer un CSV : les commandes `check-photos`,
`download-photos`, `check-complete`, `download-complete` et
`prepare-complete-errors` choisissent automatiquement le fichier le plus récent.

### Le contrôle indique `aucune URL`

N'utilise pas ce CSV avec une commande de téléchargement.

Pour le flux images, bascule sur les dossiers en erreur :

```bash
python3 orchestrator.py prepare-complete-errors --procedure-id 140205
```

### Le téléchargement affiche des erreurs

Les URLs ont probablement expiré. Relance le script correspondant dans Chrome,
puis exécute immédiatement `download-photos` ou `download-complete`.

Consulte le rapport CSV : chaque ligne contient `download_status` et
`local_path`.

## Commandes avancées

Toutes les commandes automatiques acceptent encore un CSV explicite :

```bash
python3 orchestrator.py check-photos \
  --csv "$HOME/Downloads/photos-produits-dossiers (1).csv"

python3 orchestrator.py download-complete \
  --csv "$HOME/Downloads/dossiers-complets-pieces-jointes (1).csv"
```

Le téléchargement générique reste disponible pour choisir tous les chemins :

```bash
python3 orchestrator.py download \
  --csv "/chemin/vers/le-fichier.csv" \
  --output-dir "/chemin/vers/la-sortie" \
  --report "/chemin/vers/le-rapport.csv" \
  --group-by-dossier
```
