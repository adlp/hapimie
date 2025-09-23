# hapimie
Happy l'api amie de l'AMI

![Licence: EUPL v1.2](https://img.shields.io/badge/License-EUPL%20v1.2-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Panoramisk](https://img.shields.io/badge/Panoramisk-async%20AMI%20client-green.svg)

# Le projetHapimie

Une API open source accompagnée d'une interface web, conçue pour acceder simplement a l'AMI d'asterisk

## Fonctionnalités

- API RESTful pour acceder a l'Asterisk Management Interface (AMI)
- Interface web en HTML/CSS/JS

## Installation

```bash
git clone https://github.com/adlp/hapimie.git
cd hapimie
```

## ⚖️ Licence

Ce projet est distribué sous la licence **European Union Public Licence v1.2 (EUPL)**.

Cela signifie que toute redistribution ou modification doit respecter les termes de la licence.  
La licence est juridiquement reconnue dans tous les pays de l’Union européenne et compatible avec plusieurs autres licences open source.

🔗 [Texte officiel de la licence (EUPL v1.2)](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12)  
📄 Voir le fichier [LICENSE](./LICENSE) pour plus d’informations.


### 👤 Auteur
Développé par Antoine DELAPORTE
📧 Contact : hapiomie@baball.eu
📅 Année : 2025
🤝 Contributions : [CONTRIBUTING.md](./CONTRIBUTING.md)

Les contributions sont les bienvenues !
Merci de consulter le fichier [CONTRIBUTING.md](./CONTRIBUTING.md) (à créer) pour les règles de contribution.

### 🧪 Tests
J'voudrais bien... mais bon...

### Configuration
  * Le fichier de configuration trouvera naturellement sa place là /usr/local/etc/hapimie.cfg, mais il peut etre specifié lors de l'appel d'hapimie, avec le parametre --cfgfile
```ini /usr/local/etc/hapimie.cfg
API_PORT= 8888
API_HOST= 0.0.0.0
API_PATH= /api
AMI_HOST= 127.0.0.1
AMI_PORT= 5038
AMI_USER= asterisk
AMI_PASS= Sangoku
MAX_RETRIES= 3
RETRY_DELAY= 3
SECRET_KEY= supersecretkey
ALGORITHM= HS256
TOKEN_EXPIRY_HOURS= 2
AUTHENTIK_ENABLED= False
AUTHENTIK_TOKEN_URL= https://authentik.example.com/application/o/token/
AUTHENTIK_CLIENT_ID= your-client-id
AUTHENTIK_CLIENT_SECRET= your-client-secret
```
    * Les parametres commencant par API_ permettent de configurer les basique de l'api : son port d'ecoute, l'ip sur laquelle elle ecoute et le chemin de l'aou
    * Les parametres commencant par AMI_ permettent de configurer les acces à l'AMI d'asterisk (host asterisk, port de l'ami, login et mot de passe)
    * MAX_RETRIES et RETRY_DELAY sont pour les auto-reconnexion a l'AMI en cas de perte de connexion
    * SECRET, ALGORITHM et TOKEN_EXPIRY_HOUR permettent de configurer le comportement du token
    * AUTHENTIK_ sont les parametres de configuration de l'authentification passant par un serveur authentik

  * Lors du premier usage il convient de creer un compte et un mot de passe, le fichier des utilisateurs est users.csv dans le meme repertoire que hapimie
```bash
> ./manage_users 
usage: manage_users [-h] [--email EMAIL] [--gecos GECOS] file login
manage_users: error: the following arguments are required: file, login
> ./manage_users --email phonemaster@example.com --gecos "Phone Admin" users.csv admin
➕ Création de l'utilisateur 'admin'
Mot de passe : 
Confirmer : 
✅ Fichier mis à jour : users.csv
```

