from pathlib import Path
import subprocess
import sys

def install_requirements(requirements_path, pip_target_dir='/srv/pip-install', marker_file='/tmp/required'):
    """
    Installe les dépendances depuis un fichier requirements.txt si nécessaire.

        Ex:install_requirements( "/srv/bordoc/requirements.txt", "/srv/pip-install", "/tmp/required")
    
    Args:
        requirements_path: chemin vers le fichier requirements.txt
        pip_target_dir: répertoire cible pour l'installation pip
        marker_file: fichier marqueur pour vérifier si l'installation est à jour
    """
    requirements_path = Path(requirements_path)
    pip_target_dir = Path(pip_target_dir)
    marker_file = Path(marker_file)

    # Vérifier si le fichier requirements existe
    if not requirements_path.exists():
        print(f"Erreur: {requirements_path} n'existe pas")
        return

    # Déterminer si l'installation est nécessaire
    needs_install = False

    if not marker_file.exists():
        needs_install = True
        print(f"Installation nécessaire: le marqueur {marker_file} n'existe pas")
    else:
        # Comparer les timestamps
        req_mtime = requirements_path.stat().st_mtime
        marker_mtime = marker_file.stat().st_mtime

        if req_mtime > marker_mtime:
            needs_install = True
            print(f"Installation nécessaire: {requirements_path} est plus récent que {marker_file}")

    # Installer si nécessaire
    if needs_install:
        print(f"Installation des dépendances dans {pip_target_dir}...")

        # Créer le répertoire cible s'il n'existe pas
        pip_target_dir.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements_path),
                "--target", str(pip_target_dir)
            ])

            # Créer/mettre à jour le fichier marqueur
            marker_file.parent.mkdir(parents=True, exist_ok=True)
            marker_file.touch()

            print("Installation terminée avec succès")
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'installation: {e}")
            sys.exit(1)
    else:
        print("Les dépendances sont déjà à jour")
    # Ajouter le répertoire au PYTHONPATH pour pouvoir importer les modules
    #sys.path.insert(0, pip_target_dir)
    # sauf que ca ne marche pas... si ca n'est pas juste avant les imports... les vrais


