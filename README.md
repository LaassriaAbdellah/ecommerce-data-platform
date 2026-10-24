# ShopFlow — Real-Time E-Commerce Data Platform

Projet pédagogique Data Engineering sous Windows et VS Code, pour un PC de 8 Go de RAM annoncés. Objectif : consolider commandes, clients et paiements et produire des indicateurs fiables sans double comptage.

## État du projet

Phase 0 terminée ; **phase 1 en cours** : données Olist présentes, exploration Jupyter Orders/Customers et validateurs Python/Pandas Orders, Customers, Order Items, Payments, Products, Sellers, Reviews, Geolocation et Category Translation mutualisés existants. Aucun pipeline PostgreSQL, orchestration ou streaming implémenté. Voir [la roadmap](AGENTS.md), [la progression](docs/PROGRESS.md) et [les décisions](docs/ARCHITECTURE_DECISIONS.md).

Projet officiel : C:\Users\PC\Documents\Projets stage\ecommerce-data-platform. Utiliser exclusivement son .venv. D: est exclu du développement ; ne pas accéder à ses fichiers ni les modifier.

## Données et organisation

Source déclarée : [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Les neuf CSV sont présents dans data/, non suivis par Git. Provenance détaillée et conditions/licence restent à documenter.

- notebooks/01_data_exploration.ipynb : exploration des commandes, dates, statuts, doublons et références clients.
- src/validation/orders_validator.py : validate_orders(orders, customers) et point d'entrée main().
- tests/test_orders_validator.py : cinq tests Orders ; tests/test_environment.py : deux tests d'environnement ; quatorze autres tests pour common, le moteur et Customers.
- data/processed/ : CSV validé et rapport JSON, ignorés par Git.
- sql/ et docker/ : emplacements préparés, aucun service configuré.
- requirements.txt : dépendances existantes, Pandas et ipykernel verrouillés sur les versions installées.
- .env.example : modèle sans secret, non chargé automatiquement ; .gitkeep conserve les dossiers vides.

## Environnement et dépendances

Python 3.11.0 du .venv local. À l'audit du 2026-10-23 : pandas 3.1.0, numpy 2.4.6, pytest 9.1.1 et ipykernel 7.4.0 présents ; pip check sans incohérence. Les paquets notebook et jupyterlab ne sont pas installés ; VS Code peut utiliser ipykernel pour ses notebooks.

Pandas 3.1.0 et ipykernel 7.4.0 sont désormais déclarés dans requirements.txt (2026-10-24), sans réinstallation. Les dépendances transitives de phase 1 ne sont pas toutes verrouillées ; aucune reconstruction dans un environnement neuf effectuée pendant cet audit.

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

## Validateur Order Items

Implémenté après l'exploration, en phase 1. Il réutilise common.py et quality_engine.py sans modifier les validateurs Orders/Customers.

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.order_items_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_order_items_validator.py -q -p no:cacheprovider
```

Prérequis : data/olist_order_items_dataset.csv et data/olist_orders_dataset.csv. La commande **remplace** uniquement les sorties dérivées order_items_validated.csv et order_items_quality_report.json dans data/processed/.

Résultat réel du 2026-10-24 : **112 650 lignes valides, 0 à examiner** ; dix règles à zéro. Le rapport générique utilise entity=order_items, total_rows, valid_rows, review_rows et anomalies_by_rule. Aucun CSV source modifié.

Contrôles : sept colonnes obligatoires, IDs non vides, clé composite unique (order_id, order_item_id), numéro entier positif, référence Orders existante, prix fini >0, transport fini >=0, date limite présente/convertible. Les booléens ne constituent pas des valeurs numériques acceptables.

La comparaison de clé utilise le numéro converti, sans modifier la colonne d'origine. Les clés incomplètes/invalides ont leur propre motif, sans doublon artificiel. Les colonnes de qualité sont calculées par le moteur existant.

Le helper de dates accepte un date_format optionnel ; seul ce nouveau validateur utilise mixed pour des dates convertibles de formats différents. Les autres appels conservent leur comportement par défaut. Les dates manquantes et non convertibles ont des motifs séparés.

Les 383 transports nuls sont acceptés. Les 127 échéances avant approbation, les 10 423 remises après échéance et les quatre échéances en 2020 ne deviennent pas des erreurs structurelles ; les indicateurs métier restent séparés. Payments et Products sont documentés ci-dessous.

## Validateur Payments

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.payments_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_payments_validator.py -q -p no:cacheprovider
```

Le module réutilise common.py et quality_engine.py sans modifier les validateurs existants. Il lit data/olist_order_payments_dataset.csv et les order_id de Orders, puis **remplace** seulement data/processed/payments_validated.csv et payments_quality_report.json. Aucun CSV source n'est modifié.

Résultat réel du 2026-10-24 : **103 886 lignes valides, 0 à examiner**. Sept règles structurelles toutes à zéro : identifiant absent, clé composite dupliquée, référence inconnue, séquence invalide, échéanciers invalides, montant invalide et type absent.

La clé est (order_id, payment_sequential), pas order_id seul. La conversion numérique sert aux contrôles et à l'équivalence des clés (1 et "1"), sans corriger les valeurs sources. Séquence entière >0 ; échéanciers entiers >=0 ; montant fini >=0 ; booléens refusés. payment_type doit être non vide, sans liste fermée imposée.

Le rapport conserve entity/total_rows/valid_rows/review_rows/anomalies_by_rule et ajoute une section **business_indicators** :

| Indicateur | Unité | Résultat |
|---|---|---:|
| zero_payment_value_rows | lignes | 9 |
| zero_payment_installments_rows | lignes | 2 |
| not_defined_payment_type_rows | lignes | 3 |
| orders_sequence_not_starting_at_1 | commandes distinctes | 80 |

Ces indicateurs ne modifient ni quality_status, ni quality_issue_count, ni quality_issues ; ils ne s'additionnent pas aux anomalies. Les commandes dont un compteur de séquence est invalide/absent sont exclues du dernier indicateur, afin de ne pas conclure sur un groupe incomplet. Les frais/montants nuls et not_defined ne sont pas automatiquement des erreurs.

Les paiements multiples sont acceptés et payment_value n'est jamais multiplié par payment_installments. La commande livrée sans paiement reste un futur contrôle inter-tables, hors de ce validateur. Pas de chiffre d'affaires comptable déduit de ces données.

## Validateur Products

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.products_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_products_validator.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
```

Le module lit data/olist_products_dataset.csv et product_category_name_translation.csv. validate_products(products, translations) réutilise les helpers et le moteur existants. Il remplace uniquement data/processed/products_validated.csv et products_quality_report.json, ignorés par Git.

Neuf colonnes obligatoires ; product_id renseigné et unique. Les sept champs numériques sont facultatifs : nulls, chaînes vides et espaces sont des absences autorisées. Toute valeur renseignée doit être convertible, finie et >=0 ; les trois compteurs descriptifs/photos doivent aussi être entiers. Les booléens sont refusés. L'orthographe Olist lenght et les valeurs sources sont conservées ; aucun seuil maximal imposé.

Résultat réel du 2026-10-24 : **32 951 produits valides, 0 à examiner**, neuf règles structurelles à zéro. Le rapport conserve entity/total_rows/valid_rows/review_rows/anomalies_by_rule et ajoute business_indicators et descriptive_statistics.

| Indicateur séparé | Nombre |
|---|---:|
| Produits sans catégorie | 610 |
| Produits avec au moins un des trois compteurs descriptifs/photos absent | 610 |
| Produits avec poids ou dimension absent | 2 |
| Produits avec au moins un des neuf champs absent (union) | 611 |
| Produits avec poids égal à zéro | 4 |
| Produits dans une catégorie sans traduction | 13 |
| Catégories distinctes sans traduction | 2 |

Ces indicateurs ne changent pas les colonnes de qualité. Une catégorie absente n'est pas comptée comme catégorie sans traduction. La correspondance exige un nom source et une traduction anglaise non vides ; elle utilise l'appartenance, sans jointure multipliant les lignes. Les absences simultanées sont comptées une seule fois dans l'union.

Les extrêmes sont décrits par min, médiane, P99 (interpolation linéaire) et max pour chaque colonne, uniquement sur les valeurs présentes structurellement valides. Ces statistiques ne constituent pas des seuils de rejet.

## Validateur Sellers

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.sellers_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_sellers_validator.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

validate_sellers(sellers, items, customers) réutilise les helpers et le moteur existants ; les 27 codes d'État sont importés de Customers, sans changer son comportement. Quatre colonnes obligatoires, ID renseigné/unique, préfixe renseigné de cinq chiffres ASCII, ville renseignée, État renseigné/reconnu. Les absences de préfixe/État ne sont pas recomptées comme formats invalides.

La lecture et le résultat utilisent string pour seller_zip_code_prefix ; aucune remise à cinq chiffres ni correction automatique. Si un zéro a été perdu avant l'appel, il n'est pas inventé. Relire le CSV exporté avec dtype={"seller_zip_code_prefix": "string"}.

Le point d'entrée lit Sellers, seller_id d'Order Items et les trois colonnes géographiques de Customers, puis remplace seulement data/processed/sellers_validated.csv et sellers_quality_report.json. Résultat réel du 2026-10-24 : **3 095 vendeurs valides, 0 à examiner ; sept règles à zéro**.

Le rapport générique conserve entity/total_rows/valid_rows/review_rows/anomalies_by_rule et ajoute :
- inter_table_checks.order_items_seller_references : statut pass/fail, lignes Item à ID absent/inconnu, IDs inconnus distincts, vendeurs non référencés. Résultat : 112 650 lignes, zéro absence/inconnue et zéro vendeur inutilisé ; pass. Une référence absente ne modifie pas la qualité d'un vendeur existant.
- business_indicators : indicateurs géographiques sans effet sur les colonnes de qualité.
- indicator_methodology : définitions, limites, unités et exclusion des valeurs non comparables.

| Indicateur | Résultat |
|---|---:|
| Groupes de variantes de ville, à État identique | 6 |
| Vendeurs appartenant à ces groupes (toutes écritures incluses) | 723 |
| Préfixes multi-États / vendeurs concernés | 17 / 45 |
| Préfixes multivilles / vendeurs concernés | 34 / 112 |
| Vendeurs avec préfixe non observé dans Customers | 91 |
| Vendeurs comparables sur l'État / sur la ville | 3 004 / 3 004 |
| Vendeurs avec écart d'État / de ville normalisée | 35 / 89 |

Clé de ville : casefold, NFKD, retrait des accents, ponctuation remplacée par espaces, espaces réduits. Les valeurs originales ne sont pas remplacées. Comparaisons par ensembles observés pour un préfixe, sans jointure multipliant les lignes. Les groupes sans valeur Customer comparable sont exclus des écarts.

**Customers n'est pas un référentiel géographique officiel.** Ces groupes peuvent se chevaucher, ne pas les additionner ni considérer leurs membres comme des erreurs confirmées. Les 723 lignes incluent les écritures fréquentes de référence. Voir l'[exploration Sellers](docs/SELLERS_EXPLORATION.md).

## Validateur Reviews

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.reviews_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviews_validator.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

validate_reviews(reviews, orders) réutilise les helpers communs et le moteur existant, sans modifier leur comportement. Sept colonnes obligatoires, IDs renseignés, paire (review_id, order_id) unique, note finie entière de 1 à 5 (booléens exclus), dates renseignées/convertibles et référence Orders existante. Un même review_id sur plusieurs commandes est autorisé. Clés incomplètes et dates absentes ne sont pas recomptées comme doublons/dates invalides.

Orders doit fournir order_id unique/non vide, order_purchase_timestamp et order_delivered_customer_date. Une référence Orders ambiguë provoque une erreur explicite, sans choisir arbitrairement une date.

Le point d'entrée lit les deux CSV sources puis remplace uniquement data/processed/reviews_validated.csv et reviews_quality_report.json, ignorés par Git. Les sept colonnes sources restent identiques ; seules les trois colonnes de qualité sont ajoutées. Résultat réel du 2026-10-24 : **99 224 avis valides, 0 à examiner ; neuf règles à zéro**.

Le rapport générique ajoute business_indicators, answer_delay_days et indicator_methodology. Les commentaires facultatifs, avis multiples et chronologies inhabituelles n'affectent pas la qualité.

| Indicateur | Résultat |
|---|---:|
| Titres absents / messages absents (espaces seuls inclus) | 87 658 / 58 274 |
| Deux commentaires absents | 56 537 |
| Commandes avec plusieurs avis / notes différentes | 547 / 202 |
| Commandes sans avis | 768 |
| Créations / réponses avant achat | 74 / 63 |
| Créations avant livraison : horodatage / jour calendaire | 8 320 / 5 127 |
| Réponses avant livraison | 4 795 |
| Paires comparables à la livraison | 96 359 |
| Créations avec commande connue sans livraison exploitable | 2 865 |
| Créations à minuit | 99 139 |

Multiplicité calculée sur les paires complètes distinctes, références inconnues incluses ; une paire dupliquée n'est pas un avis supplémentaire. Les notes différentes sont comptées après conversion numérique, en excluant les groupes avec une note invalide. Une commande possède un avis dès qu'une paire complète la référence, même si la note ou une date est invalide.

Délais en jours de 24 h : médiane 1,6749 ; moyenne 3,1490 ; P95 6,9722 ; P99 22,0708 ; maximum 518,6992. Aucun délai négatif/nul dans la source ; ils resteraient indicateurs. Statistiques sans paire valide : null, pas NaN.

Dates Olist sans fuseau, conversion mixed pour les contrôles seulement. Chaque comparaison exclut les dates absentes/non convertibles et rapporte son nombre de paires comparables. Comparaison calendaire après normalisation à minuit ; ne pas confondre précision du jour et de l'heure, ni supposer une réponse du vendeur. Aucun remplissage ou seuil de rejet temporel. Voir l'[exploration Reviews](docs/REVIEWS_EXPLORATION.md).

## Validateur Geolocation

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.geolocation_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_geolocation_validator.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

validate_geolocation(geolocation, sellers, customers) vérifie les cinq colonnes, le préfixe renseigné de cinq chiffres ASCII, les coordonnées présentes/numériques/finies dans [-90,90] et [-180,180], ville non vide, État renseigné dans les 27 codes réutilisés de Customers. Bornes inclusives ; booléens refusés comme coordonnées. Absences séparées des valeurs invalides, sans double comptage.

Aucune unicité du préfixe, aucun seuil régional ou de dispersion, aucun rejet des doublons complets. Le préfixe reste string, sans padding. Les autres colonnes sources sont préservées. Relire le CSV exporté avec dtype={"geolocation_zip_code_prefix": "string"}.

Résultat réel du 2026-10-24 : **1 000 163 lignes valides, 0 à examiner ; neuf règles à zéro**. Le point d'entrée lit Geolocation avec coordonnées string et villes/États category, puis les trois champs géographiques Sellers/Customers. Il remplace seulement data/processed/geolocation_validated.csv et geolocation_quality_report.json, ignorés par Git.

| Indicateur séparé | Résultat |
|---|---:|
| Doublons complets excédentaires | 261 831 |
| Préfixes à plusieurs coordonnées valides | 17 781 |
| Triplets préfixe/latitude/longitude distincts valides | 720 154 |
| Préfixes multivilles / multi-États | 8 556 / 8 |
| Groupes de variantes de ville à État identique | 2 128 |
| Dispersion maximale latitude / longitude (degrés) | 77,025708 / 72,552315 |

| Couverture | Sellers | Customers |
|---|---:|---:|
| Lignes couvertes | 3 088 | 99 163 |
| Lignes à préfixe absent | 7 | 278 |
| Préfixes distincts absents | 7 | 157 |
| Écarts d'État / de ville sur préfixes connus | 35 / 89 | 0 / 24 |
| Préfixes Geolocation non observés dans la table | 16 776 | 4 178 |

Le rapport générique ajoute business_indicators, coordinate_dispersion, coverage, indicator_methodology et execution_seconds. Les indicateurs n'affectent pas les trois colonnes de qualité. Coordonnées distinctes et étendues calculées sur les seules paires finies dans les bornes mondiales, sans arrondi ; unités degrés, pas kilomètres. Variantes : casefold/NFKD/sans accents/ponctuation en espaces/espaces réduits.

Couverture par appartenance à des préfixes/paires distincts, sans jointure brute multipliant les lignes. Préfixes invalides dans une référence séparés des absences ; villes non vides et États reconnus comparés seulement sur préfixes connus. Les groupes peuvent se chevaucher. Geolocation n'est ni officiel ni exhaustif ; aucun point n'est attribué individuellement à un vendeur/client.

Performance : masques vectorisés et signatures NumPy des neuf règles. Le moteur de qualité inchangé sérialise seulement les combinaisons distinctes (au plus 512), puis les trois colonnes sont étendues par position. Équivalence au moteur original testée sur les 512 combinaisons avec répétitions et index non unique.

Mesure de cette exécution, pas un benchmark garanti : lecture 2,590 s ; validation avec indicateurs 6,730 s ; export CSV 3,918 s. Pas de pic mémoire mesuré. Contrôle du CSV par blocs de 100 000 lignes : cinq champs sources identiques, 245 733 zéros initiaux conservés. Voir l'[exploration](docs/GEOLOCATION_EXPLORATION.md).

## Validateur Category Translation

```powershell
.\.venv\Scripts\python.exe -B -m src.validation.category_translation_validator
.\.venv\Scripts\python.exe -B -m pytest tests/test_category_translation_validator.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

validate_category_translation(translations, products) réutilise les helpers et le moteur existants. Deux colonnes obligatoires ; catégorie portugaise et traduction anglaise renseignées/non vides. L'unicité anglaise n'est pas imposée.

Les deux motifs de clé sont **exclusifs** :
- conflicting_category_translation : toutes les lignes d'une catégorie portugaise renseignée possédant plusieurs traductions distinctes non vides ;
- duplicate_product_category_name : toutes les occurrences d'une catégorie renseignée répétée qui n'est pas dans un groupe contradictoire.

Une contradiction ne déclenche donc pas aussi le motif de doublon. Les absences de champs sont indépendantes : une ligne sans traduction dans un groupe contradictoire possède deux problèmes distincts. Les clés absentes ne deviennent pas des doublons. quality_issue_count compte les règles indépendantes par ligne ; review_rows compte chaque ligne une seule fois. Comparaisons exactes sans trim/casefold pour les règles ; les variantes normalisées restent des indicateurs. Cette politique précise la proposition historique de l'exploration.

Le point d'entrée lit product_category_name_translation.csv et la catégorie de Products, puis remplace uniquement data/processed/category_translation_validated.csv et category_translation_quality_report.json. Aucune traduction ajoutée ; toutes les lignes et valeurs sources sont conservées.

Résultat réel du 2026-10-24 : **71 traductions valides, 0 à examiner ; quatre règles à zéro**.

| Indicateur séparé | Résultat |
|---|---:|
| Catégories Products sans traduction | 2 |
| pc_gamer | 3 produits |
| portateis_cozinha_e_preparadores_de_alimentos | 10 produits |
| Produits concernés au total | 13 |
| Produits sans catégorie (séparés) | 610 |
| Catégories traduites inutilisées | 0 |
| Libellés anglais partagés | 0 |
| Produits sur catégorie à traduction contradictoire | 0 |
| Groupes de variantes portugaises / anglaises | 0 / 0 |

Le rapport générique ajoute business_indicators, writing_indicators et rule_semantics. La couverture signifie au moins une paire complète, sans choisir une traduction si elle est contradictoire ; les produits concernés par ces ambiguïtés sont comptés séparément. Une catégorie Products absente est exclue des catégories non traduites.

Les indicateurs listent aussi les catégories inutilisées, les libellés anglais partagés avec leurs catégories et les variantes sous normalisation exploratoire. Ils n'affectent pas la qualité. Les contrôles ne prouvent pas la justesse linguistique. Voir l'[exploration](docs/CATEGORY_TRANSLATION_EXPLORATION.md).

## Tests PowerShell

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_orders_validator.py -v -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Résultats actuels (2026-10-24) : suite complète **569 passed in 18.06s** (540 tests existants et 29 nouveaux cas Category Translation). pip check sans incohérence. Couverture encore partielle des autres validateurs.

## Git, ressources et suite

```powershell
git status --short --branch
git check-ignore -v data/olist_orders_dataset.csv data/processed/orders_validated.csv data/processed/orders_quality_report.json
```

Seul data/.gitkeep est suivi sous data/. Le notebook, le module et les tests de phase 1 sont encore non suivis au début de l'audit. Aucun commit/push sans accord.

Dépôt : https://github.com/LaassriaAbdellah/ecommerce-data-platform ; HEAD vérifié : 7df7e27. Documentation en français ; code et noms techniques en anglais, snake_case, tests test_*.py.

Exploration order_items réalisée en lecture seule le 2026-10-24 : voir [le rapport](docs/ORDER_ITEMS_EXPLORATION.md) et notebooks/02_order_items_exploration.ipynb. Le validateur est désormais implémenté et ses résultats attendent validation de l'étudiant ; Products est désormais implémenté et testé ; ses résultats attendent validation. Sellers est désormais implémenté et testé, en attente de validation. Reviews est désormais implémenté et testé, en attente de validation. Geolocation est désormais implémenté et testé, en attente de validation ; aucun dataset suivant commencé. Cela ne modifie pas la roadmap : restent notamment les contrôles inter-tables, la vérification de reconstruction des dépendances, le dictionnaire, le schéma source et les cas limites. Aucun PostgreSQL ni phase suivante lancé. Aucun service lourd requis ; Docker/WSL2 restent à vérifier lors d'une phase qui en a besoin.

Les événements de streaming futurs seront synthétiques et séparés des sources historiques ; les paiements en BRL ne sont pas automatiquement un chiffre d'affaires comptable.
