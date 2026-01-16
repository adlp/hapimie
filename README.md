# Hapimie

> Happy l'API amie de l'AMI

![Licence: EUPL v1.2](https://img.shields.io/badge/License-EUPL%20v1.2-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Panoramisk](https://img.shields.io/badge/Panoramisk-async%20AMI%20client-green.svg)

API REST open source accompagnée d'une interface web pour accéder simplement à l'AMI d'Asterisk.

## Fonctionnalités

- **API RESTful** pour l'Asterisk Management Interface (AMI)
- **Interface web** personnalisable (Jinja2/CSS/JS)
- **Authentification** locale (CSV/bcrypt) et OIDC (Authentik, Keycloak...)
- **Cache intelligent** pour réduire la charge sur Asterisk
- **Connexion AMI persistante** avec reconnexion automatique
- **Contrôle d'accès** par groupes (ACL)
- **Audit trail** des actions utilisateurs

## Installation rapide

### Via pip

Non recommandée...

```bash
git clone https://github.com/adlp/hapimie.git
cd hapimie
pip install -e .
```

### Via Docker

```bash
git clone https://github.com/adlp/hapimie.git
cd hapimie
cp .env.example .env
# Éditer .env avec vos paramètres
docker-compose -f docker/docker-compose.yml up -d
```

## Configuration

### 1. Variables d'environnement

Copiez `.env.example` en `.env` et adaptez :

```bash
cp .env.example .env
```

Variables principales :

| Variable        | Description                 | Défaut      |
| --------------- | --------------------------- | ----------- |
| `AMI_HOST`      | Adresse du serveur Asterisk | `127.0.0.1` |
| `AMI_PORT`      | Port AMI                    | `5038`      |
| `AMI_USER`      | Utilisateur AMI             | `hapimie`   |
| `AMI_PASS`      | Mot de passe AMI            | -           |
| `SECRET_KEY`    | Clé secrète pour JWT        | -           |
| `API_PORT`      | Port d'écoute               | `8888`      |
| `HAPACL_FULL`   | Groupe admin                | `admin`     |
| `HAPACL_Status` | Groupe lecture              | `users`     |

### 2. Fichier de configuration (optionnel)

```bash
cp config/hapimie.cfg.example config/hapimie.cfg
```

### 3. Utilisateurs locaux

Pour l'authentification locale, créez un fichier `users.csv` :

```
login:password_hash:nom:email:groups
admin:$2b$12$...:Admin:admin@example.com:admin,users
```

Générer un hash de mot de passe :

```bash
./scripts/manage_users users.csv username --email user@example.com
```

## Lancement

### Développement

```bash
# Avec Python
python -m hapimie

# Avec Docker (inclut Asterisk de test)
docker-compose -f docker/docker-compose.dev.yml up -d
```

### Production

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## Structure du projet

```
hapimie/
├── src/hapimie/          # Code source (package Python)
│   ├── core/             # Client AMI, cache
│   ├── web/              # Framework web, auth
│   ├── config/           # Gestion configuration
│   ├── validation/       # Validation des entrées
│   ├── exceptions/       # Exceptions personnalisées
│   └── logging/          # Logging et audit
│
├── config/               # Fichiers de configuration
│   ├── asterisk/         # Config Asterisk (dev)
│   └── hapimie.cfg.example
│
├── docker/               # Fichiers Docker
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── docs/                 # Documentation
├── scripts/              # Utilitaires
├── tests/                # Suite de tests
├── templates/            # Templates Jinja2
└── static/               # Fichiers statiques
```

## API

### Endpoints principaux

| Méthode | Endpoint         | Description               | ACL    |
| ------- | ---------------- | ------------------------- | ------ |
| GET     | `/api/status`    | Channels actifs           | Status |
| GET     | `/api/endpoints` | Liste des endpoints       | Status |
| GET     | `/api/queue`     | Statut des queues         | Status |
| GET     | `/api/dbGet`     | Base de données Asterisk  | Full   |
| POST    | `/api/HangUp`    | Raccrocher un channel     | Full   |
| GET     | `/api/help`      | Commandes AMI disponibles | -      |

Documentation complète : [docs/api-reference.md](docs/api-reference.md)

## Extensibilité

Hapimie peut être étendu avec vos propres routes et templates :

```python
from hapimie import app, asti

# Ajouter un template personnalisé
app.add_template('mon_template_dir')

# Ajouter une route
@app.api_add("/api/ma-route", daType='json', acl='users')
async def ma_route(var_session, params={}):
    result = await asti.channels()
    return result

app.run()
```

## Tests

```bash
# Tests unitaires
pytest tests/unit/ -v

# Avec couverture
pytest tests/ --cov=hapimie --cov-report=html

# Tests avec Docker (incluant Asterisk)
docker-compose -f docker/docker-compose.dev.yml --profile test up tests
```

## Documentation

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Référence API](docs/api-reference.md)
- [Architecture](docs/architecture.md)
- [Développement](docs/development.md)
- [Dépannage](docs/troubleshooting.md)

## Sécurité

Voir [SECURITY.md](SECURITY.md) pour :

- Signaler une vulnérabilité
- Bonnes pratiques de déploiement
- Configuration sécurisée

## Licence

Ce projet est distribué sous la licence **European Union Public Licence v1.2 (EUPL)**.

[Texte officiel de la licence](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12) | [LICENSE](LICENSE)

## Auteur

Développé par **Antoine DELAPORTE**

- Contact : hapimie@baball.eu
- Contributions : [CONTRIBUTING.md](CONTRIBUTING.md)
