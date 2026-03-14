# XML TV Fr

XML TV Fr est un service permettant de récupérer un guide des programmes au format XMLTV.

Site web et documentation : https://xmltvfr.fr/


# Installation

## Prérequis

XML TV Fr utilise **Python ≥ 3.12**.  
La façon recommandée d'obtenir la bonne version est d'utiliser [pyenv](https://github.com/pyenv/pyenv).

### 1. Installer pyenv (si besoin)

```bash
# Linux / macOS via le script officiel
curl https://pyenv.run | bash
```

Ajoutez ensuite ces lignes à votre `~/.bashrc` (ou `~/.zshrc`) et relancez votre shell :

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

### 2. Installer Python 3.12 avec pyenv

```bash
pyenv install 3.12
pyenv local 3.12      # définit Python 3.12 pour ce dépôt
```

### 3. Créer et activer un environnement virtuel

Placez-vous à la racine du dépôt, puis :

```bash
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
```

### 4. Installer le paquet et ses dépendances

Le code Python se trouve dans le dossier `python/`. Installez-le en mode
éditable (ce qui rend la commande `xmltvfr` disponible directement dans le
venv) :

```bash
cd python
pip install -e .
```

Pour installer également les dépendances de développement (linter, tests…) :

```bash
pip install -e ".[dev]"
```

## Utilisation de Docker

Vous pouvez utiliser XML TV Fr avec Docker.

Un fichier [Dockerfile](./Dockerfile) à la racine du projet vous permet
d'installer et configurer XML TV Fr en une seule commande.

### Construire l'image

```bash
docker build -t xmltvfr .
```

> Cette commande doit être lancée après chaque mise à jour de XML TV Fr.


# Configuration

## Liste des chaines (`config/channels.json`)

La liste des chaines doit être indiquée dans le fichier `channels.json` au
format JSON. Chaque chaine correspond à l'ID d'une chaine (exemple :
`France2.fr`) présente dans les fichiers de chaines par services (dossier
`channels_by_providers`).

La structure d'un item se fait comme ceci :

```json
"IdDelaChaineDansLeProgramme": {
  "name": "Nom de la chaine",
  "alias": "IDdeLaChaineDansLeXMLTV",
  "icon": "http://icone-de-la-chaine",
  "priority": ["Service1", "Service2"]
}
```

Les champs `name`, `icon`, `alias` et `priority` sont **optionnels**.

- **`priority`** : donne un ordre de priorité différent de celui par défaut en
  indiquant les noms des services (nom des classes dans le dossier
  `python/xmltvfr/providers/`). Dans l'exemple, `Service1` sera appelé en
  premier et `Service2` ne sera appelé que si `Service1` échoue. Si aucun
  programme n'est trouvé sur tous les services, la chaine est indiquée *HS*
  pour le jour concerné.
- **`alias`** : donne un ID alternatif à une chaine. Si le champ est absent,
  c'est l'ID par défaut renseigné dans XML TV Fr qui sera affiché.

## Configuration du programme (`config/config.json`)

Copiez le fichier d'exemple fourni et adaptez-le à vos besoins :

```bash
cp resources/config/default_config.json config/config.json
cp resources/config/default_channels.json config/channels.json
```

Le fichier `config.json` est au format JSON :

```jsonc
{
  "days": 8,                  // Nombre de jours de l'EPG
  "cache_max_days": 8,        // Nombre de jours de cache
  "output_path": "var/export/", // Chemin de destination du XML final
  "delete_raw_xml": false,    // Supprimer le XML brut après génération
  "enable_gz": true,          // Activer la compression gz
  "enable_zip": true,         // Activer la compression zip
  "enable_xz": false,         // Activer la compression xz (nécessite 7-Zip)
  "7zip_path": null,          // Chemin vers le binaire 7-Zip (xz uniquement)
  "enable_dummy": false,      // Afficher un EPG mire si aucune donnée trouvée
  "custom_priority_orders": { "Telerama": 0.2, "UltraNature": 0.5 },
  "guides_to_generate": [
    { "channels": "config/channels.json", "filename": "xmltv.xml" }
  ],
  "nb_threads": 1,            // Threads en parallèle (défaut : 1)
  "min_timerange": 79200,     // (22 h) Plage min. d'un cache pour être complet
  "force_todays_grab": false, // Forcer le re-téléchargement du jour courant
  "ui": "MultiColumnUI"       // Affichage terminal : MultiColumnUI | ProgressiveUI
}
```


# Lancer le script

Les commandes ci-dessous supposent que le venv est actif (`source .venv/bin/activate`)
et que vous êtes à la racine du dépôt.

## Générer l'EPG (natif)

```bash
xmltvfr export
```

Options disponibles :

| Option | Description |
|---|---|
| `--skip-generation` | Réalise l'export sans récupérer de nouvelles données (cache uniquement) |
| `--keep-cache` | Conserve le cache même s'il est expiré |

## Autres commandes

```bash
# Récupérer le programme d'une chaine pour un provider et une date donnés
xmltvfr fetch-channel TF1.fr Orange 2025-12-14 content.xml

# Mettre à jour les logos par défaut depuis un provider
xmltvfr update-default-logos MyCanal

# Afficher l'aide
xmltvfr help
```

## Via Docker

```bash
# Générer l'EPG (commande par défaut)
docker run -v ./var/export:/app/var/export -v ./config/:/app/config xmltvfr

# Afficher l'aide
docker run --rm xmltvfr xmltvfr help

# Récupérer le programme d'une chaine pour un provider et une date donnés
docker run --rm -v ./var/cache:/app/var/cache xmltvfr xmltvfr fetch-channel TF1.fr Orange 2025-12-14 content.xml

# Mettre à jour les logos par défaut depuis un provider
docker run --rm xmltvfr xmltvfr update-default-logos MyCanal
```

Remplacez `./var/export` par le dossier de sortie souhaité.


# Lancer les tests

Les tests unitaires utilisent [pytest](https://pytest.org). Assurez-vous
d'avoir installé les dépendances de développement (voir plus haut), puis :

```bash
cd python
pytest
```

Pour afficher la couverture de code :

```bash
pytest --cov=xmltvfr --cov-report=term-missing
```

Pour lancer uniquement le linter :

```bash
ruff check xmltvfr/
```


# Sortie

## Logs

Les logs de génération sont écrits dans `var/logs/` au format JSON après
chaque exécution en mode `debug` (activé par défaut via la commande
`xmltvfr export`).

## Fichiers XML TV

Les fichiers de sortie sont stockés dans le dossier défini par `output_path`
(par défaut `var/export/`) aux formats XML, ZIP et/ou GZ selon la
configuration.


# Automatisation GitHub Actions

## Image Docker (GHCR)

L'image Docker est construite et publiée automatiquement sur
**GitHub Container Registry** à chaque push sur la branche `master` qui modifie
`Dockerfile` ou le code Python (`python/**`).

| Image | Description |
|---|---|
| `ghcr.io/chrcl/xml-tv-fr:latest` | Dernière version de la branche `master` |
| `ghcr.io/chrcl/xml-tv-fr:master` | Tag de branche |
| `ghcr.io/chrcl/xml-tv-fr:sha-<sha>` | Tag de commit exact |

Le workflow correspondant est [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml).  
Le workflow [`.github/workflows/docker.yml`](.github/workflows/docker.yml) valide la construction de
l'image lors des Pull Requests.

## Génération XMLTV (workflow réutilisable)

Le workflow [`.github/workflows/generate-xmltv.yml`](.github/workflows/generate-xmltv.yml)
est **réutilisable** (`workflow_call`).  Il utilise l'image GHCR pour générer
les fichiers EPG sans reconstruire l'image.

### Paramètres d'entrée

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `channels_file` | string | `channels/all.json` | Chemin relatif vers le fichier de chaines |
| `days` | number | `8` | Nombre de jours d'EPG à générer (1–14) |
| `output_name` | string | `xmltv` | Nom de base du fichier de sortie (sans extension) |
| `nb_threads` | number | `4` | Nombre de threads parallèles |
| `artifact_name` | string | `xmltv-output` | Nom de l'artefact GitHub Actions produit |
| `image_tag` | string | `latest` | Tag de l'image GHCR à utiliser |

### Appeler le workflow depuis un autre workflow

```yaml
jobs:
  my-generation:
    uses: chrcl/XML-TV-Fr/.github/workflows/generate-xmltv.yml@master
    with:
      channels_file: channels/tnt.json
      days: 7
      output_name: xmltv-tnt
      artifact_name: xmltv-tnt
```

### Présets de chaines disponibles

| Fichier | Description |
|---|---|
| `channels/all.json` | Toutes les chaines (232 chaines) |
| `channels/tnt.json` | Chaines TNT françaises gratuites (20 chaines) |

Pour créer un préset personnalisé, ajoutez un fichier JSON dans `channels/` en
vous inspirant du format de `channels/all.json`.

## Génération quotidienne et publication sur GitHub Pages

Le workflow [`.github/workflows/daily.yml`](.github/workflows/daily.yml) s'exécute
**chaque jour à 03h00 UTC** (et peut être déclenché manuellement).  Il appelle
le workflow réutilisable pour chaque configuration définie dans la matrice, puis
publie l'ensemble des fichiers générés sur **GitHub Pages**.

### Ajouter ou modifier une configuration

Modifiez la section `matrix.config` dans `daily.yml` :

```yaml
matrix:
  config:
    # Configuration existante
    - channels_file: channels/all.json
      days: 8
      output_name: xmltv-all
      artifact_name: xmltv-all
    # Nouvelle configuration
    - channels_file: channels/ma-selection.json
      days: 3
      output_name: xmltv-ma-selection
      artifact_name: xmltv-ma-selection
```

### Fichiers publiés

Les fichiers générés sont accessibles sur GitHub Pages sous
`https://<owner>.github.io/<repo>/` :

| Fichier | Description |
|---|---|
| `index.html` | Page d'index avec liens de téléchargement |
| `xmltv-all.xml` | EPG complet (XML brut) |
| `xmltv-all.xml.gz` | EPG complet (gzip) |
| `xmltv-all.xml.zip` | EPG complet (zip) |
| `xmltv-tnt.xml` | EPG TNT (XML brut) |
| `xmltv-tnt.xml.gz` | EPG TNT (gzip) |
| `xmltv-tnt.xml.zip` | EPG TNT (zip) |

> **Prérequis GitHub Pages :** activez GitHub Pages depuis les paramètres du
> dépôt → *Pages* → source **GitHub Actions**.

---

# Ajouter des services (Providers)

Il est possible d'ajouter des services (`Provider`) autres que ceux fournis.
Pour cela, créez un fichier dans `python/xmltvfr/providers/` qui hérite de
`AbstractProvider` :

```python
# python/xmltvfr/providers/mon_provider.py
from xmltvfr.providers.abstract_provider import AbstractProvider
from xmltvfr.domain.models.channel import Channel


class MonProvider(AbstractProvider):
    def __init__(self, client, json_path, priority):
        # Le fichier JSON listant les chaines supportées par ce provider
        super().__init__(client, "python/xmltvfr/providers/json/MonProvider.json", priority)

    @classmethod
    def get_priority(cls) -> float:
        # Flottant entre 0 et 1 ; comparez aux autres providers pour vous situer
        return 0.5

    def construct_epg(self, channel: str, date: str) -> Channel | bool:
        channel_obj = super().construct_epg(channel, date)

        # Récupérez et peuplez les programmes ici
        for result in self._fetch_schedule(channel, date):
            program = channel_obj.add_program(result["start_ts"], result["end_ts"])
            program.add_title(result["title"])          # lang="fr" par défaut
            program.add_icon(result.get("icon"))
            program.add_category(result.get("category"))
            program.add_desc(result.get("description"))

        if channel_obj.get_program_count() == 0:
            return False
        return channel_obj
```

> **Important :** le nom de la classe doit correspondre exactement au nom du
> fichier (sans `.py`). Le découvreur de providers se base sur ce nom pour
> l'enregistrement automatique.
