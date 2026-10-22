# AGENTS.md — Real-Time E-Commerce Data Platform

> Document de référence pour Codex et pour l'étudiant. À placer à la racine du dépôt. Lire intégralement avant toute modification. Langue de travail : français (code, noms techniques et conventions en anglais).

## 1. Mission et règles non négociables

Construire **progressivement** une plateforme Data Engineering e-commerce, à visée portfolio/PFE, sur **Windows + VS Code, 8 Go de RAM**. L'étudiant apprend chaque technologie **en développant**. Ne jamais implémenter plusieurs phases d'un seul coup.

À chaque intervention de Codex :
1. Lire ce fichier et `docs/PROGRESS.md` (si présent), inspecter l'état réel du dépôt et identifier la **prochaine tâche non terminée**.
2. Proposer **une seule petite tâche** cohérente (objectif, notion, fichiers, commandes, tests et critère de succès). Attendre l'accord de l'utilisateur avant une nouvelle phase ou une modification architecturale importante.
3. Expliquer avant de coder : problème métier, concepts fondamentaux, alternatives, pourquoi la technologie est choisie, contraintes mémoire, et ce qui sera vérifié.
4. Implémenter seulement la tâche convenue ; privilégier des modifications petites, compréhensibles, reproductibles et testées.
5. Donner les commandes **PowerShell** exactes, préciser le résultat attendu, expliquer les erreurs et demander à l'étudiant de confirmer sa compréhension.
6. Mettre à jour `docs/PROGRESS.md` avec date, phase, tâche, état (`TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`), fichiers changés, tests réellement exécutés, problèmes et prochaine action. Ne jamais déclarer un test réussi s'il n'a pas été exécuté.
7. Ne pas passer à l'étape suivante sans validation des critères d'acceptation et confirmation de l'utilisateur.
8. Ne pas inventer des réalisations, résultats de benchmarks, performances ou métriques. Ne pas présenter des données simulées comme réelles.
9. Respecter la structure existante et ne pas écraser des fichiers ou secrets. Expliquer toute migration avant de l'effectuer.
10. Maintenir le périmètre **Data Engineering** : pas de Machine Learning, RAG, agents IA ou frontend complexe sans demande explicite.

**Règle de progression** : MVP batch/SQL fiable → transformations/dbt → orchestration → lake/Parquet/Spark → streaming/Kafka → qualité/CI/CD/observabilité → Cloud optionnel. Chaque phase doit rester démontrable indépendamment.

## 2. Problème métier et résultat attendu

Entreprise fictive **ShopFlow** : consolider commandes, clients, produits, paiements et livraisons ; produire des indicateurs fiables sur les revenus, volumes, annulations, retards, régions et produits. Exploiter le dataset historique **Olist Brazilian E-Commerce** (source : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), puis générer **séparément** des événements synthétiques pour le streaming.

Questions métier :
- Combien de commandes sont passées, livrées, annulées par jour et par région ?
- Quel est le montant des paiements et comment éviter de compter deux fois les commandes multi-paiements/multi-articles ?
- Quels produits/catégories/vendeurs performent ?
- Quelle est la durée de livraison et la proportion de livraisons en retard ?
- Les pipelines ont-ils traité toutes les données, sans duplication ni perte ?

**Définir les KPI précisément** : date de référence, grain (commande / ligne de commande / paiement), devise BRL, statut des commandes, gestion des remboursements non documentés, valeurs manquantes, fuseaux horaires. Ne pas assimiler automatiquement « paiements » à « chiffre d'affaires comptable ».

## 3. Contraintes techniques et ressources

- PC : **8 Go RAM**, Windows/PowerShell, VS Code. Vérifier la version de Python, l'espace disque, WSL2/Docker et les ports avant installation ; ne rien supposer.
- Démarrer **sans** Spark, Kafka, Airflow ou Metabase. Ne jamais lancer la stack entière simultanément.
- Limiter mémoire/CPU des conteneurs, préférer des services à la demande, un petit dataset, des lectures par lots (`chunksize`) et un PySpark `local[2]` avec mémoire contrôlée. Arrêter les services non utilisés.
- Si Docker Desktop/WSL2 est trop lourd, PostgreSQL local est acceptable pour le MVP ; noter l'écart et conserver un chemin de migration Docker.
- Les services Cloud sont **optionnels** ; ne jamais déclencher de frais ou créer des ressources payantes sans autorisation. Préférer les offres gratuites uniquement après vérification des conditions.
- Le disque externe peut stocker les données volumineuses, mais éviter les bases de données sur un disque instable ou débranchable.
- Aucun secret, token, mot de passe ni dataset massif dans Git. `.env` ignoré ; `.env.example` sans secrets ; GitHub Actions utilise des secrets si nécessaire.

## 4. Stack cible et ordre d'apprentissage

| Ordre | Technologie | Rôle / compétences à acquérir | Statut |
|---|---|---|---|
| 1 | Python 3.11+ | fichiers, API, exceptions, logging, typage, packaging, batch | Obligatoire |
| 1 | SQL avancé / PostgreSQL | DDL, contraintes, index, JOIN, CTE, fenêtres, EXPLAIN, transactions | Obligatoire |
| 1 | Git / GitHub / pytest | versionnement, branches, tests, documentation | Obligatoire |
| 2 | SQLAlchemy / psycopg | connexion, transactions, chargement par lots | Obligatoire |
| 3 | dbt Core + dbt-postgres | modèles, `source`, `ref`, tests, documentation, incremental | Obligatoire |
| 4 | Apache Airflow | DAG, schedule, retries, backfill, idempotence, dépendances | Obligatoire, mode léger |
| 5 | Parquet + MinIO (S3 compatible) | object storage, partitions, schéma, formats colonnes | Important |
| 6 | PySpark local | transformations distribuées, lazy evaluation, shuffle, partitions | Important |
| 7 | Kafka (mode KRaft) | producer, consumer, offsets, partitions, clés, delivery semantics | Important, isolé |
| 8 | Delta Lake | ACID, schema evolution, MERGE, bronze/silver/gold | Option avancée si compatible |
| 8 | GitHub Actions | lint, tests, validation CI | Important |
| 8 | Metabase | tableaux de bord KPI | Optionnel |
| 9 | Azure/Databricks ou équivalent | stockage et exécution cloud, IAM, coûts | Optionnel, autorisation préalable |

**Important** : les versions doivent être **compatibles entre elles**, notamment Java/Spark/Delta, Python/Airflow et dbt/adaptateur. Vérifier les matrices officielles au moment de l'installation et verrouiller les versions après test. Ne pas installer des outils uniquement pour cocher une case.

## 5. Architecture cible (à construire par incréments)

```text
SOURCES HISTORIQUES (Olist CSV)              EVENEMENTS SYNTHETIQUES
           |                                           |
       Python ingestion                           Kafka producer
           |                                           |
   PostgreSQL raw (MVP)                       Kafka topics (phase 7)
           |                                           |
       dbt staging                               Kafka consumer
           |                                           |
    dbt marts / SQL                          stockage append-only
           |                                           |
 PostgreSQL Data Warehouse                MinIO / Parquet / Spark
           |                                           |
       Metabase                            Bronze -> Silver -> Gold

       Airflow = orchestration batch (après MVP)
       Tests / Logs / GitHub Actions = transversal
```

Ne pas confondre **Data Lake (objets Parquet)**, **Data Warehouse (tables relationnelles)** et **Lakehouse (tables avec métadonnées/transactions, ex. Delta)**. Décrire les chemins de circulation et les sources de vérité à chaque évolution.

## 6. Source Olist : données et règles

Dataset : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Fichiers pertinents :
- `olist_orders_dataset.csv` : `order_id`, `customer_id`, statuts, dates.
- `olist_customers_dataset.csv` : `customer_id`, `customer_unique_id`, ville, état.
- `olist_order_items_dataset.csv` : `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value`.
- `olist_order_payments_dataset.csv` : `order_id`, `payment_sequential`, `payment_type`, `payment_value`.
- `olist_products_dataset.csv` : `product_id`, catégories et attributs.
- `olist_sellers_dataset.csv` : vendeurs.
- `olist_geolocation_dataset.csv` : optionnel, volumineux.
- `product_category_name_translation.csv` : catégories traduites.
- `olist_order_reviews_dataset.csv` : optionnel.

**Précautions de modélisation** :
- `customer_id` représente un enregistrement de client par commande ; `customer_unique_id` rapproche des clients récurrents.
- Une commande peut avoir **plusieurs articles** et **plusieurs paiements**. Joindre directement items × paiements crée des multiplications de lignes et fausse les sommes : agréger séparément au grain `order_id` ou concevoir des tables de faits distinctes.
- Conserver les données sources brutes et des métadonnées d'ingestion (`ingested_at`, `source_file`, `batch_id`) si approprié.
- Définir clés, contraintes et politiques de dédoublonnage d'après le grain réel, pas par intuition.
- La donnée historique Olist n'est pas un flux temps réel : les événements Kafka seront explicitement **simulés**.
- Respecter la licence et les conditions d'utilisation du dataset ; documenter la provenance.

## 7. Roadmap détaillée et critères de validation

### Phase 0 — Préparer le dépôt et l'environnement
**Notions** : venv, dépendances, Git, `.gitignore`, configuration, secrets, structure modulaire, README.
**Tâches** : vérifier Python et RAM/disque ; créer `.venv`, `src/`, `tests/`, `sql/`, `data/`, `docs/`, `docker/`, `.env.example`, `.gitignore`, `requirements.txt` ou `pyproject.toml` ; initialiser Git ; définir conventions et commandes PowerShell.
**Validation** : environnement actif, dépendances importables, `pytest` exécutable, premier commit, aucun secret/dataset massif suivi.

### Phase 1 — Explorer les sources et concevoir l'ingestion
**Notions** : structure CSV, schéma, types, valeurs nulles, doublons, qualité, clés, grain, batch, ETL vs ELT.
**Tâches** : télécharger Olist manuellement ou via Kaggle autorisé ; explorer 3 fichiers d'abord (orders, customers, payments) ; écrire un profilage Python ; documenter dictionnaire de données, clés, volumes et anomalies ; dessiner schéma source.
**Validation** : rapport de profilage reproductible et tests simples des colonnes attendues ; pas de modification destructive des sources.

### Phase 2 — Construire un pipeline d'ingestion Python → PostgreSQL
**Notions** : DDL, schémas `raw`, types SQL, transactions, batch inserts, paramètres, index, contraintes, idempotence, upsert, reprise sur incident, logging.
**Tâches** : installer/configurer PostgreSQL ; scripts de création ; ingestion par lots ; `batch_id`, logs et compteurs ; gestion des erreurs ; stratégie de réexécution ; tests avec petit jeu de données.
**Validation** : nombre de lignes attendu, types corrects, requêtes de contrôle, réexécution sans doublons, rollback/reprise démontrés.

### Phase 3 — Modélisation dimensionnelle et dbt
**Notions** : OLTP vs OLAP, star schema, fait/dimension, grain, dimensions conformes, clés substituts, SCD notions, CTE, fenêtres, dbt `source`/`ref`, matérialisations, tests, lineage.
**Tâches** : ajouter order_items/products/sellers ; schémas `staging` et `marts` ; `stg_orders`, `stg_payments`, `stg_items` ; faits de commandes, paiements, lignes et dimensions client/produit/date ; tests `unique`, `not_null`, `relationships`, `accepted_values` ; docs dbt.
**Validation** : `dbt build` réussi, tests de qualité, KPI réconciliés avec les sources et **absence de double comptage**.

### Phase 4 — Orchestration Airflow
**Notions** : DAG, task, schedule, retries, backfill, catchup, pools, sensors, variables/connections, dépendances, idempotence, monitoring.
**Tâches** : Airflow en mode de développement compatible et peu gourmand ; DAG ingestion → contrôles → dbt ; retries ; gestion des erreurs ; journal d'exécution.
**Validation** : DAG exécutable, relance sûre, échec simulé puis reprise, logs et statut vérifiables. Ne pas lancer Kafka/Spark en parallèle.

### Phase 5 — Data Lake MinIO + Parquet
**Notions** : object storage vs fichiers locaux, S3, formats CSV/Parquet, compression, partitionnement, schema evolution, Bronze/Silver/Gold, small files.
**Tâches** : MinIO local à la demande ; dépôt des sources et snapshots Parquet ; conventions de chemins/partitions ; contrôle des volumes et des schémas.
**Validation** : fichiers lisibles, partitions pertinentes, comparaison CSV/Parquet et requêtes de contrôle.

### Phase 6 — PySpark en mode local
**Notions** : Spark DataFrames, transformations vs actions, lazy evaluation, partitions, shuffle, join strategies, cache, skew, `explain`, memory tuning.
**Tâches** : PySpark `local[2]`, jeux de données limités, lecture Parquet, nettoyage, jointures et agrégations ; écriture Silver/Gold ; comparer les résultats avec SQL/dbt.
**Validation** : résultats équivalents, schémas corrects, exécution stable sur 8 Go, plan d'exécution expliqué.

### Phase 7 — Streaming avec Kafka (isolé)
**Notions** : event time vs processing time, topics, partitions, consumer groups, offsets, keys, ordering, at-least-once, deduplication, late events, replay, schema compatibility.
**Tâches** : producteur Python de commandes **synthétiques** ; Kafka KRaft en service séparé ; consommateur Python idempotent ; persistance append-only ; métriques de débit/retard ; démonstration de replay. Spark Structured Streaming seulement si les ressources le permettent, sinon rester sur consumer Python.
**Validation** : aucune perte démontrée sur test contrôlé, dédoublonnage, redémarrage du consumer et reprise à partir des offsets ; limites documentées.

### Phase 8 — Qualité, observabilité, sécurité et CI/CD
**Notions** : tests unitaires/intégration, data contracts, fraîcheur, complétude, unicité, intégrité référentielle, logs structurés, métriques, alerting, secrets, least privilege, CI/CD.
**Tâches** : pytest ; tests SQL/dbt ; GitHub Actions (lint + tests sans services lourds) ; documentation d'exploitation ; dashboard Metabase optionnel ; jeu de démonstration.
**Validation** : CI verte réellement exécutée, échec détecté par test, guide de dépannage et commandes de reprise.

### Phase 9 — Cloud / Lakehouse avancé (optionnelle)
**Notions** : IAM, coûts, managed services, Databricks/Azure, Delta ACID/MERGE, orchestration Cloud, sécurité et gouvernance.
**Tâches** : vérifier coûts et éligibilité, obtenir consentement avant création de ressources ; migrer **une seule** partie du pipeline ; Delta Lake uniquement avec versions compatibles.
**Validation** : démonstration reproductible, coût estimé/documenté, ressources arrêtées/supprimées après usage.

### Phase 10 — Portfolio et préparation aux entretiens
**Notions** : communication technique, arbitrages, architecture, limites, tests, démonstration, STAR.
**Tâches** : README clair, diagrammes, captures, instructions de démarrage, démo batch + streaming, décisions d'architecture (ADR), problèmes rencontrés, questions d'entretien, description CV honnête.
**Validation** : une personne peut reproduire le MVP en suivant le README ; l'étudiant peut expliquer chaque composant et ses compromis.

## 8. Compétences transversales à ne pas oublier

- **SQL** : JOIN, GROUP BY, CTE, window functions, `CASE`, `COALESCE`, index, plans d'exécution, transactions, isolation.
- **Modélisation** : grain, cardinalité, clés primaires/étrangères, normalisation, schéma en étoile, SCD (concept), historisation.
- **Fiabilité** : idempotence, déduplication, retries avec backoff, checkpoints, validation de schéma, erreurs partielles, reprocessing.
- **Data quality** : fraîcheur, complétude, unicité, validité, cohérence, réconciliation, data contracts.
- **Performance** : batch sizing, partitionnement, indexation, pushdown, shuffle, skew, compression, petites partitions.
- **Sécurité** : secrets, rôles et permissions, données personnelles, anonymisation, accès minimal.
- **Ops** : logs, métriques, alertes, health checks, CI/CD, documentation, sauvegarde et restauration.
- **Coûts** : CPU/RAM/disque, stockage objet, trafic réseau, Cloud budgets.
- **Communication** : diagrammes, choix d'architecture, résultats de tests, limites connues, décisions documentées.

## 9. Structure cible du dépôt (créer au fur et à mesure)

```text
ecommerce-data-platform/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt           # ou pyproject.toml ; choisir une approche
├── data/                      # données non suivies dans Git
├── src/
│   ├── ingestion/
│   ├── quality/
│   ├── streaming/             # phase 7
│   └── common/
├── sql/
├── tests/
├── docs/
│   ├── PROGRESS.md
│   ├── DATA_DICTIONARY.md
│   ├── ARCHITECTURE.md
│   └── adr/
├── docker/                    # seulement quand nécessaire
├── dbt/                       # phase 3
├── airflow/                   # phase 4
├── spark/                     # phase 6
└── .github/workflows/         # phase 8
```

## 10. Modèle de suivi `docs/PROGRESS.md`

Si absent, créer au début du travail :

```markdown
# Progression — E-Commerce Data Platform

## État actuel
- Phase : 0
- Tâche : préparation de l'environnement
- Statut : TODO
- Dernière validation : aucune

## Journal
| Date | Phase | Tâche | Statut | Tests réellement exécutés | Remarques |
|---|---|---|---|---|---|

## Prochaine action
- Vérifier les prérequis Windows/Python/VS Code et créer le squelette minimal.

## Blocages / décisions
- Aucun pour le moment.
```

## 11. Format de réponse attendu de Codex

À chaque session, répondre brièvement avec :
1. **Où nous en sommes** (état du dépôt et de PROGRESS, sans supposition).
2. **Concept du jour** (explication pédagogique et exemple concret).
3. **Tâche unique** (fichiers à créer/modifier et pourquoi).
4. **Commandes PowerShell** et résultat attendu.
5. **Tests/validation** (ce qui a réellement été exécuté, ce que l'étudiant doit vérifier).
6. **Question de compréhension** (1 à 3 questions) et attente de confirmation.
7. **Mise à jour de PROGRESS.md**.

**Instruction de démarrage** : « Lis AGENTS.md, inspecte le dépôt et commence uniquement la phase 0. Explique les notions, propose une première petite tâche et attends ma validation avant de passer à la suivante. »
