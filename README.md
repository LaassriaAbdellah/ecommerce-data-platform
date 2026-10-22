# ShopFlow - Real-Time E-Commerce Data Platform
Projet Data Engineering sur Windows, 8 Go RAM. Phase 0 : environnement uniquement, aucun pipeline. Stack prevue : Python, PostgreSQL, dbt, Airflow, MinIO/Parquet, Spark, Kafka, CI. Voir AGENTS.md et docs/PROGRESS.md.

Organisation : src/ code ; tests/ tests ; data/ donnees ignorees ; sql/ scripts ; docker/ configurations futures ; docs/ documentation. .gitkeep conserve les dossiers vides.
.env.example : sans secret, non charge automatiquement ; .gitignore : exclusions.
Installation PowerShell : creer .venv seulement si absent avec python -m venv .venv.
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
Attendu : aucune incoherence, deux tests reussis. Selectionner .venv/Scripts/python.exe dans VS Code.
Aucun commit ni distant sans accord. Disque : environ 0,23 Gio libres, liberer avant donnees/services. Phase 1 apres confirmation.

Migration phase 0 : ouvrir D:\DataEngineering\ecommerce-data-platform dans VS Code. Garder D: branche et sa lettre stable. Python de base reste sur C: ; le venv du projet est sur D:.
PowerShell : Set-Location D:\DataEngineering\ecommerce-data-platform
Ouverture : code -n D:\DataEngineering\ecommerce-data-platform
Dans VS Code : Python: Select Interpreter, puis D:\DataEngineering\ecommerce-data-platform\.venv\Scripts\python.exe. Le chemin par defaut est configure dans .vscode/settings.json.
Les chemins relatifs des commandes installation/tests restent valides. Original sur C: conserve ; cette copie ne libere pas automatiquement son espace. Docker et WSL non reconfigures.
