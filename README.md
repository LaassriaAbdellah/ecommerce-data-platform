# ShopFlow — Real-Time E-Commerce Data Platform

Projet pédagogique Data Engineering sous Windows et VS Code, pour un PC de 8 Go de RAM annoncés. Objectif : consolider commandes, clients et paiements et produire des indicateurs fiables sans double comptage.

## État du projet

Phase 0 terminée ; **phase 1 en cours** : données Olist présentes, exploration Jupyter Orders/Customers et validateurs Python/Pandas mutualisés existants. Aucun pipeline PostgreSQL, orchestration ou streaming implémenté. Voir [la roadmap](AGENTS.md), [la progression](docs/PROGRESS.md) et [les décisions](docs/ARCHITECTURE_DECISIONS.md).

Projet officiel : C:\Users\PC\Documents\Projets stage\ecommerce-data-platform. Utiliser exclusivement son .venv. D: est exclu du développement ; ne pas accéder à ses fichiers ni les modifier.

## Données et organisation

Source déclarée : [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Les neuf CSV sont présents dans data/, non suivis par Git. Provenance détaillée et conditions/licence restent à documenter.

- notebooks/01_data_exploration.ipynb : exploration des commandes, dates, statuts, doublons et références clients.
- src/validation/orders_validator.py : validate_orders(orders, customers) et point d'entrée main().
- tests/test_orders_validator.py : cinq tests Orders ; tests/test_environment.py : deux tests d'environnement ; quatorze autres tests pour common, le moteur et Customers.
- data/processed/ : CSV validé et rapport JSON, ignorés par Git.
- sql/ et docker/ : emplacements préparés, aucun service configuré.
- requirements.txt : dépendances de phase 0 verrouillées ; dépendances de phase 1 à compléter.
- .env.example : modèle sans secret, non chargé automatiquement ; .gitkeep conserve les dossiers vides.

## Environnement et dépendances

Python 3.11.0 du .venv local. À l'audit du 2026-10-23 : pandas 3.1.0, numpy 2.4.6, pytest 9.1.1 et ipykernel 7.4.0 présents ; pip check sans incohérence. Les paquets notebook et jupyterlab ne sont pas installés ; VS Code peut utiliser ipykernel pour ses notebooks.

**Limite de reproductibilité : requirements.txt ne déclare pas encore Pandas ni ipykernel.** Son installation seule ne suffit pas pour reproduire la phase 1. Leur ajout sera une tâche distincte, avec compatibilité vérifiée et validation préalable ; aucune installation nécessaire pour l'audit actuel.

Depuis la racine sur C:, vérifier l'interpréteur et l'espace :

```powershell
.\.venv\Scripts\python.exe -B -c "import sys, shutil; print(sys.executable); print(round(shutil.disk_usage('.').free / 2**30, 3), 'GiB free')"
.\.venv\Scripts\python.exe -B -m pip check
```

Espace mesuré lors de l'audit : 7,595 Gio libres, à revérifier avant téléchargement ou installation. Conserver le venv existant. Activation facultative : `.\.venv\Scripts\Activate.ps1` ; si refusée, employer le chemin Python explicite sans modifier la politique PowerShell. Dans VS Code, sélectionner le .venv du projet pour Python **et** le noyau du notebook ; les métadonnées du notebook ne prouvent pas le noyau actuellement sélectionné.

## Exécuter le validateur

Prérequis : les CSV bruts data/olist_orders_dataset.csv et data/olist_customers_dataset.csv, ainsi que Pandas dans le venv. Depuis la racine :

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.orders_validator
```

Cette commande lit les deux sources, conserve toutes les lignes et **remplace** les sorties dérivées :
- data/processed/orders_validated.csv
- data/processed/orders_quality_report.json

Les CSV bruts ne sont pas réécrits. Le module résout les chemins depuis son emplacement ; aucun chemin absolu vers un autre disque n'est requis.

Résultat reproduit **en mémoire** pendant l'audit, sans relancer main() ni réécrire ces sorties : 99 441 lignes analysées, 99 168 valid et 273 review. Rapport JSON existant identique au recalcul et colonnes de qualité du CSV concordantes. Le détail des 18 règles et leurs nombres est dans [PROGRESS.md](docs/PROGRESS.md).

- valid : aucune règle implémentée déclenchée ; aucune garantie d'exactitude absolue.
- review : au moins une incohérence potentielle à examiner.
- quality_issue_count : nombre de règles déclenchées.
- quality_issues : chaîne JSON contenant la liste des motifs.

Une ligne n'est comptée qu'une fois dans review, même avec plusieurs motifs. Le rapport compte des **lignes**, pas des order_id distincts ; sur ce fichier, aucun order_id dupliqué n'a été trouvé.

Les dates manquantes ne sont pas inventées et aucune commande n'est supprimée automatiquement. La conversion se fait sur une copie ; les dates non convertibles sont signalées. Les dates d'achat/estimées déjà nulles restent une limite à traiter. Les dates n'ont pas encore de fuseau explicite documenté.

Le notebook a des totaux concordants, mais sa liste quality_issues n'est pas reconstruite après l'ajout des dernières règles : utiliser le pipeline pour les motifs complets.

## Validation mutualisée et Customers

- src/validation/common.py : colonnes requises, identifiants manquants/dupliqués et dates invalides.
- src/validation/quality_engine.py : apply_quality_rules(), contrôles des masques et génération des trois colonnes de qualité et du rapport.
- src/validation/customers_validator.py : sept règles et point d'entrée main().
- tests/test_common.py, test_quality_engine.py et test_customers_validator.py complètent les tests existants.

Customers : 99 441 lignes, 96 096 customer_unique_id distincts et 2 997 identifiants récurrents. La répétition de customer_unique_id est normale ; la clé attendue de la ligne reste customer_id. Les sept règles détectent les identifiants absents/dupliqués, les villes/États absents, les préfixes postaux invalides et les États non autorisés.

Depuis la racine, avec le venv existant :

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.customers_validator
```

Cette commande lit data/olist_customers_dataset.csv avec customer_zip_code_prefix en string pour préserver les zéros initiaux. Un préfixe doit contenir cinq chiffres ; ne pas le lire comme un entier.

Elle **remplace** data/processed/customers_validated.csv et customers_quality_report.json, sans modifier le brut. Rapport Customers : entity, total_rows, valid_rows, review_rows, anomalies_by_rule. Orders conserve ses clés historiques total_orders/valid_orders/review_orders via adaptation du rapport générique.

À l'audit du 2026-10-23 : Customers 99 441 lignes valid, 0 review ; Orders toujours 99 441 lignes dont 273 review. Rapports et colonnes de qualité sauvegardés comparés aux fonctions appelées en mémoire, sans réexécuter les main() ni réécrire les sorties. Zéro anomalie ne garantit pas l'exactitude absolue des adresses.

## Tests PowerShell

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_orders_validator.py -v -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Résultats actuels : cinq tests Orders ciblés ; suite complète **21 passed in 0.80s**, réellement exécutée pendant l'audit (2 environnement, 5 Orders, 4 common, 5 moteur, 5 Customers). Couverture encore partielle.

## Git, ressources et suite

```powershell
git status --short --branch
git check-ignore -v data/olist_orders_dataset.csv data/processed/orders_validated.csv data/processed/orders_quality_report.json
```

Seul data/.gitkeep est suivi sous data/. Le notebook, le module et les tests de phase 1 sont encore non suivis au début de l'audit. Aucun commit/push sans accord.

Dépôt : https://github.com/LaassriaAbdellah/ecommerce-data-platform ; HEAD vérifié : 7df7e27. Documentation en français ; code et noms techniques en anglais, snake_case, tests test_*.py.

Prochaine demande : explorer order_items en lecture seule puis définir ses règles, uniquement après accord. Aucun travail order_items commencé ici. Cela ne modifie pas la roadmap : restent notamment payments, les dépendances reproductibles, le dictionnaire, le schéma source et les cas limites. Aucun PostgreSQL ni phase suivante lancé. Aucun service lourd requis ; Docker/WSL2 restent à vérifier lors d'une phase qui en a besoin.

Les événements de streaming futurs seront synthétiques et séparés des sources historiques ; les paiements en BRL ne sont pas automatiquement un chiffre d'affaires comptable.
