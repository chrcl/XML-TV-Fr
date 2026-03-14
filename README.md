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
docker run -v ./var/export:/app/var/export -v ./config/:/app/config xmltvfr
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
