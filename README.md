# hapimie
Happy l'api amie de l'AMI

![Licence: EUPL v1.2](https://img.shields.io/badge/License-EUPL%20v1.2-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Panoramisk](https://img.shields.io/badge/Panoramisk-async%20AMI%20client-green.svg)

# Le projet Hapimie

Une API open source accompagnée d'une interface web, conçue pour acceder simplement a l'AMI d'asterisk

L'interface web est aisement surchargeable, integre une auth local mais aussi openid, afin de presenter a votre facon votre acces a l'api

Afin de decharger l'AMI d'asterisk, le projet ouvre une connexion permanante (evite ainsi les login/logout permanant) a l'AMI, puis pour certaines fonctionnalités gere un cache


## TODO
Creation de token pour bot d'API

## Fonctionnalités

- API RESTful pour acceder a l'Asterisk Management Interface (AMI)
- Interface web en HTML(djinja)/CSS/JS

## ⚖️ Licence

Ce projet est distribué sous la licence **European Union Public Licence v1.2 (EUPL)**.

Cela signifie que toute redistribution ou modification doit respecter les termes de la licence.  
La licence est juridiquement reconnue dans tous les pays de l’Union européenne et compatible avec plusieurs autres licences open source.

🔗 [Texte officiel de la licence (EUPL v1.2)](https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12)  
📄 Voir le fichier [LICENSE](./LICENSE) pour plus d’informations.

# Comment on le lance ?

## Installation

Dans un repertoire de votre choix deployez le git

```bash
git clone https://github.com/adlp/hapimie.git
cd hapimie
```

## Configuration
  - copiez le dot.env.sample en .env, et adaptez le a votre environement
  - copiez le hapimie-sample.cfg, dans le repertoire que pointeras DOHAPIMIETC et adaptez le a vos besoins

## user.csv
Si on desire faire une authentification local, le fichier user.csv devra se situer dans l'arbo presentée par DOHAPIMIETC
Il sera au format login:password_hash:nom:email:groups
Exemple de generation de mot de passe : 
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'monmotdepasse', bcrypt.gensalt()).decode())"
```

## Lancement
  - Ce projet s'appuie sur une image officielle de python, donc oui il met des données dans le /var/lib/docker, mais pour le moment pas jugées trop volumineuse.
  - Il suffit juste de faire un ```docker-compose up -d```. Le contenaire cherchera les outils dont il a besoin (pip install via requierement.txt) puis se lancera

# Extensionabilite
L'idee est que vous puissiez rajouter, modifier l'interface (API et WUI) en fonction de l'usage de votre asterisk.
  - Vous presentez a votre contenaire l'arbo de l'extension (dans mon cadre, mon application c'est ASTEC, je vous laisse regarder : la conf d'integration est la.. pour le moment :P)
  - dans le .env vous positionnez le nom d'appel de votre appli
  - En fonction de vos besoins, votre appli (en python) pourra contenir cela:
```python
#!/usr/bin/env python3

import sys
import os

# Chemin absolu vers le dossier 'kernel'
kernel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'hapimie'))

# Ajout au chemin d'import
if kernel_path not in sys.path:
    sys.path.insert(0, kernel_path)

#import hapimie
#hapimie.app.run()

from hapimie import app,asti

[...]

# Destruction de toutes les routes par defaut
#if Debug == 0:
#    routeToKill=app.api_lst()
#    for verb in routeToKill.keys():
#        for route in routeToKill[verb]:
#            if route.startswith('/log'):
#                continue
#            app.api_del(route,verb)

# Creation du nouvel environnement
app.add_template('astemplate')
app.api_add("/",form_newHome)
app.api_add("/standard",form_gestStd,acl=os.getenv('HAPACL_Status',None))
app.api_add("/api/std_status",api_std_status,acl=os.getenv('HAPACL_FULL',None))
app.api_add("/api/std_status",api_std_status,verb="POST",acl=os.getenv('HAPACL_FULL',None))

# Et... C'est partiiiiiiiiiiiiii
print('Ready to Get Connexion')
app.run()
```

Cela permettra de recreer la route / vers votre appli a vous, de meme que la route /standard (mais avec une gestion des droits en fonction du groupe de votre Utilisateur)


# Doc a ameliorer
## Configuration
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
SENTRY_DSN=sentry-url'n-token
```
    * Les parametres commencant par API_ permettent de configurer les basique de l'api : son port d'ecoute, l'ip sur laquelle elle ecoute et le chemin de l'aou
    * Les parametres commencant par AMI_ permettent de configurer les acces à l'AMI d'asterisk (host asterisk, port de l'ami, login et mot de passe)
    * MAX_RETRIES et RETRY_DELAY sont pour les auto-reconnexion a l'AMI en cas de perte de connexion
    * SECRET, ALGORITHM et TOKEN_EXPIRY_HOUR permettent de configurer le comportement du token
    * AUTHENTIK_ sont les parametres de configuration de l'authentification passant par un serveur authentik
    * SENTRY_DSN permet de remonter les plantage de l'appli. Si la configuration sentry est prise en compte le message "Sentry enabled" apparaitra au demarrage

  * Lors du premier usage il convient de creer un compte et un mot de passe, le fichier des utilisateurs est users.csv dans le meme repertoire que hapimie

# 🧪 Tests
J'voudrais bien... mais bon...

# 👤 Auteur
Développé par Antoine DELAPORTE
📧 Contact : hapiomie@baball.eu
📅 Année : 2025
🤝 Contributions : [CONTRIBUTING.md](./CONTRIBUTING.md)

Les contributions sont les bienvenues !
Merci de consulter le fichier [CONTRIBUTING.md](./CONTRIBUTING.md) (à créer) pour les règles de contribution.

