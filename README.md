# insarviz_gps


git clone https://github.com/mjaspard/insarviz_gps.git		# cloner le repo modifié

cd insarviz_gps									# aller dans le repertoire

python -m venv env								# créer un environnement python 
	
source env/bin/activate							# activer l’environnement

python -m pip install -r requirements.txt				# Installer tous les packages python nécessaire

python -m pip install .							# Installer InSAR_viz

ts_viz										# Lancer l'appli
