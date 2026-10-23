# Progression — E-Commerce Data Platform

## Bilan courant — refactorisation et Customers — 2026-10-23
- Phase 1 : IN_PROGRESS. Tâche documentaire de cette intervention : DONE.
- Fichiers modifiés par cette intervention : docs/PROGRESS.md, docs/ARCHITECTURE_DECISIONS.md, README.md. AGENTS.md inchangé : aucune progression à corriger dans la roadmap elle-même.
- common.py présent avec check_required_columns(), check_missing_ids(), check_duplicate_ids(), check_invalid_dates().
- quality_engine.py présent : apply_quality_rules() contrôle les masques (Series booléenne, index identique), remplace les valeurs indéterminées par False, génère les trois colonnes de qualité et un rapport générique entity/total_rows/valid_rows/review_rows/anomalies_by_rule.
- Orders réutilise common et le moteur, puis adapte le rapport aux clés historiques total_orders/valid_orders/review_orders ; règles et résultats locaux inchangés.
- Customers : validate_customers() et main() présents ; sept règles : missing_customer_id, duplicate_customer_id, missing_customer_unique_id, missing_customer_city, missing_customer_state, invalid_zip_code, invalid_customer_state.
- Grain Customers : customer_id identifie la ligne client liée à une commande ; customer_unique_id rapproche un même client sur plusieurs commandes et ne doit pas être unique.
- Recalcul sur le CSV : 99 441 lignes, 96 096 customer_unique_id distincts ; 2 997 de ces identifiants apparaissent sur plusieurs lignes. Il s'agit de clients récurrents déduits du grain Olist, pas de 2 997 lignes dupliquées.
- Notebook existant notebooks/01_data_exploration.ipynb : cellules Customers présentes (lecture avec préfixe postal texte et contrôles de colonnes) ; notebook inspecté, non réexécuté.
- Lecture Customers avec dtype={"customer_zip_code_prefix": "string"} pour conserver les zéros initiaux. Format attendu : cinq chiffres ; 27 codes d'État autorisés.
- Résultats en mémoire : Customers 99 441 valid_rows, 0 review_rows, sept règles à zéro. Orders 99 441 total_orders, 99 168 valid_orders, 273 review_orders.
- Quatre sorties existantes vérifiées : orders_validated.csv, orders_quality_report.json, customers_validated.csv, customers_quality_report.json sous data/processed/. Rapports JSON et trois colonnes de qualité identiques aux recalculs.
- Aucun main() relancé : aucune sortie ni source brute réécrite pendant l'audit.
- Commande exécutée : .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider ; 21 passed in 0.80s : environnement 2, Orders 5, common 4, moteur 5, Customers 5.
- Le test moteur nommé test_multiple_anomalies couvre plusieurs lignes/règles mais pas deux motifs sur la même ligne ; ce cas est couvert au niveau Orders par le test multi-anomalies.
- Espace C: mesuré : 7,595 Gio ; aucune installation ou téléchargement. requirements.txt reste limité à la phase 0, Pandas et ipykernel non déclarés : reconstruction de l'environnement de phase 1 encore incomplète.
- Validation documentaire : relecture et git diff --check : aucune erreur (sortie 0).
- Aucun code, test, notebook ou donnée modifié ; changements préexistants préservés. Aucun commit/push ni accès à D:.

## Prochaine étape (non commencée, accord requis)
- Demande de l'étudiant : explorer ensuite olist_order_items_dataset.csv, en lecture seule, et définir les règles avant de créer son validateur.
- Commencer par le grain attendu (order_id, order_item_id), les types, nulls, doublons et références ; ne pas joindre directement items et paiements.
- Cette exploration anticipée ne modifie pas l'ordre des phases : payments, dictionnaire de données, schéma source et provenance/licence restent à compléter en phase 1 ; pas de dbt, modélisation de phase 3 ou PostgreSQL lancé.
- Restent : dépendances reproductibles ; couverture des règles/cas limites encore partielle ; date d'achat absente non signalée et dates sans fuseau explicite, limites antérieures non corrigées.
- La suite est proposée uniquement ; aucun order_items exploré ou validé pendant cet audit.

## Historique des interventions précédentes
Les nombres de tests et les mentions de Customers non commencé ci-dessous sont historiques et remplacés par le bilan courant.

## Test multi-anomalies — 2026-10-23
- Phase 1 ; tâche autorisée : test_multiple_issues_count_order_once ; statut : DONE.
- Fichiers modifiés : tests/test_orders_validator.py et docs/PROGRESS.md.
- Cas synthétique : une commande delivered sans date de livraison et avec client inconnu, plus une commande témoin valide.
- Vérifie deux motifs JSON sans doublon, quality_issue_count=2, review_orders=1, valid_orders=1 et les compteurs par règle ; témoin sans motif.
- Commande exécutée : .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider ; résultat : 7 passed in 0.64s (5 tests validateur et 2 environnement).
- git diff --check : aucune erreur. Pipeline et données inchangés ; aucun commit/push.
- Prochaine action proposée : choisir un cas structurel manquant (identifiant vide ou doublonné), après confirmation. Les nombres de tests des audits ci-dessous sont historiques.

## État actuel — 2026-10-23
- Phase : 1 — exploration Olist et validation de orders ; statut global : IN_PROGRESS.
- Phase 0 : terminée ; développement exclusivement sur C:, avec le .venv local. Aucun accès à D:.
- Tâche de cette intervention : audit de l'existant et mise à jour documentaire ; statut : DONE.
- Fichiers documentaires modifiés : README.md, docs/PROGRESS.md et docs/ARCHITECTURE_DECISIONS.md ; AGENTS.md inchangé.
- Périmètre autorisé : documentation uniquement ; aucun changement du pipeline, des tests, du notebook ou des données, aucun commit/push.
- Les constats ci-dessous remplacent les mentions antérieures de phase 1 non commencée.

## Travaux inspectés et vérifiés
- Neuf CSV présents dans data/ : orders, customers, order_items, order_payments, order_reviews, products, sellers, geolocation et product_category_name_translation, avec les noms Olist complets.
- Provenance déclarée par l'étudiant : Brazilian E-Commerce Public Dataset by Olist, https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. Conditions/licence et modalités d'acquisition restent à consigner ; aucun téléchargement réalisé pendant cet audit.
- Notebook réel : notebooks/01_data_exploration.ipynb (34 cellules). Contient exploration des types, nulls, doublons, statuts, dates et références clients. Métadonnées Python 3.11.0 et noyau python3 ; sélection effective du noyau VS Code non vérifiable ici.
- Les sorties sauvegardées du notebook concordent avec les totaux et règles métier ci-dessous. Notebook lu, non réexécuté.
- Module réel : src/validation/orders_validator.py ; validate_orders(orders, customers) et main() présents. Le fichier singulier src/validation/order_validator.py visible dans un onglet n'existe pas sur disque.
- tests/test_orders_validator.py : quatre cas (valid, livraison manquante, expédition avant achat, client inconnu). tests/test_environment.py : deux contrôles d'environnement.
- Sorties existantes : data/processed/orders_validated.csv et orders_quality_report.json. Rapport JSON identique au recalcul en mémoire ; trois colonnes de qualité du CSV identiques au résultat recalculé.
- git check-ignore confirme brut et sorties ignorés ; git ls-files data ne retourne que data/.gitkeep.
- Au début de l'audit : trois documents déjà modifiés, notebook/module/tests de phase 1 non suivis. Changements existants conservés ; HEAD 7df7e27, aucun commit créé.

## Résultats recalculés sur les CSV locaux
- Orders : 99 441 lignes, 8 colonnes brutes ; grain attendu : une commande par order_id.
- CSV validé : 99 441 lignes, 11 colonnes ; 99 168 valid, 273 review.
- Les règles ci-dessous détectent des incohérences potentielles. valid signifie seulement « aucune règle implémentée déclenchée ».
- Le code compte les lignes, pas les order_id distincts : l'équivalence avec les commandes est vérifiée sur ce fichier sans doublons.
- Les dates sont converties sur une copie en mémoire ; les valeurs manquantes sont conservées, sans imputation ni suppression automatique.

| Colonne brute | Valeurs manquantes |
|---|---:|
| order_id | 0 |
| customer_id | 0 |
| order_status | 0 |
| order_purchase_timestamp | 0 |
| order_approved_at | 160 |
| order_delivered_carrier_date | 1 783 |
| order_delivered_customer_date | 2 965 |
| order_estimated_delivery_date | 0 |

| Règle implémentée | Détections |
|---|---:|
| missing_order_id | 0 |
| missing_customer_id | 0 |
| duplicate_order_id | 0 |
| unknown_customer | 0 |
| invalid_order_status | 0 |
| missing_delivery_date | 8 |
| missing_approval_date | 14 |
| missing_carrier_date | 2 |
| shipping_before_purchase | 166 |
| delivery_before_shipping | 23 |
| delivery_before_purchase | 0 |
| estimated_delivery_before_purchase | 0 |
| delivery_before_approval | 61 |
| invalid_order_purchase_timestamp | 0 |
| invalid_order_approved_at | 0 |
| invalid_order_delivered_carrier_date | 0 |
| invalid_order_delivered_customer_date | 0 |
| invalid_order_estimated_delivery_date | 0 |

Les trois règles de dates manquantes concernent seulement les commandes delivered. Les comparaisons chronologiques s'appliquent à tous les statuts et ne déclenchent pas sur NaT. Les cinq règles invalid_* détectent une valeur non nulle impossible à convertir.

- Contrôles en mémoire : aucun doublon exact, order_id dupliqué, customer_id dupliqué dans orders ou dans customers ; aucune référence client inconnue.
- Les identifiants nuls, vides ou composés d'espaces sont couverts par missing_order_id/missing_customer_id ; aucun déclenchement ici.
- 274 déclenchements de règles pour 273 lignes review : le code agrège les règles par ligne sans additionner leurs détections pour calculer review_orders.
- Écarts temporels positifs recalculés, en heures :

| Incohérence | Nombre | Médiane | Maximum |
|---|---:|---:|---:|
| Expédition avant achat | 166 | 0,5999 | 4 109,0981 |
| Livraison avant transporteur | 23 | 39,8644 | 386,3081 |
| Livraison avant approbation | 61 | 24,8233 | 167,7517 |

## Vérifications réellement exécutées pendant cet audit
- .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider : 6 passed in 1.00s (quatre tests validateur + deux environnement).
- .venv/Scripts/python.exe -B -m pip check : No broken requirements found.
- Appel direct de validate_orders() sur CSV lus : rapport recalculé et comparé au JSON existant ; comparaison des trois colonnes de qualité au CSV existant, concordance.
- main() non exécuté : aucune réécriture des sorties. Aucun CSV brut, notebook ou fichier de test modifié.
- Versions installées lues : pandas 3.1.0, numpy 2.4.6, pytest 9.1.1, ipykernel 7.4.0. Paquets notebook et jupyterlab absents ; leur absence n'empêche pas les notebooks VS Code avec ipykernel.
- Espace C: mesuré : 7,475 Gio. Aucune installation ou téléchargement.
- Essais ponctuels en mémoire : date d'achat absente reste valid sur un exemple sinon cohérent ; deux lignes de même order_id donnent review_orders=2 et duplicate_order_id=2.
- Contrôle documentaire : relecture et git diff --check exécutés ; aucune erreur, sortie 0.

## Écarts et limites constatés
- requirements.txt ne déclare ni Pandas ni l'environnement notebook ; pip check valide les paquets présents, pas la reproductibilité depuis ce fichier. Correction à autoriser séparément.
- Le notebook construit quality_issues avec cinq règles avant les ajouts finaux et ne reconstruit pas la liste ensuite : ses totaux finaux concordent, mais ses motifs ne doivent pas être assimilés à ceux du pipeline.
- Le notebook examine approval_before_purchase (0 dans sa sortie sauvegardée) ; cette règle exploratoire n'est pas intégrée au validateur.
- Le validateur ne signale pas une date d'achat ou date estimée absente si elle est déjà nulle. Les dates non convertibles deviennent NaT sur la copie et sont signalées par invalid_*.
- Les doublons de customer_id dans customers sont comptés dans le rapport sans rendre une commande review. Les doublons exacts et ceux de customer_id dans orders sont contrôlés dans l'exploration, pas par des règles dédiées du pipeline.
- Le rapport compte les lignes impliquées dans duplicate_order_id (keep=False), pas les identifiants distincts ni uniquement les occurrences excédentaires.
- Pas de chargement par lots : deux DataFrames complets et copies en mémoire. Aucun benchmark mémoire réalisé ; ne pas généraliser aux fichiers volumineux.
- Les dates n'ont pas de fuseau explicite ; aucune conversion UTC justifiée à ce stade.

## Prochaine petite tâche recommandée (accord requis)
- Compléter les tests du validateur orders : anomalie multiple sur une ligne, identifiants manquants/vides/dupliqués, statuts invalides, dates invalides, colonnes obligatoires et non-mutation des entrées.
- Critère prioritaire : une ligne avec plusieurs motifs compte une seule fois dans review_orders, avec quality_issue_count et quality_issues cohérents. Définir séparément le comportement attendu pour les doublons et dates obligatoires manquantes avant de changer le code.

## Tâches restantes de phase 1
- Rendre les dépendances Pandas et notebook reproductibles, après accord et vérification de compatibilité ; ne rien installer pour l'audit.
- Compléter les tests manquants des règles temporelles et des cas limites (table vide, valeurs NaT, schémas incomplets).
- Formaliser les contrôles structurels et le grain ; ne pas supprimer/dédoublonner sans décision explicite.
- Mettre à jour le notebook pour harmoniser les motifs si demandé, en conservant la séparation exploration/pipeline.
- Créer le dictionnaire des données et le schéma source (absents actuellement), documenter provenance/licence et conventions de dates.
- Explorer customers et payments progressivement ; pas de validation customers commencée par cette intervention.
- Envisager des helpers partagés seulement après identification de règles communes réelles.
- Phase 2 PostgreSQL non commencée ; accord requis avant toute nouvelle phase.

## Historique antérieur conservé
Les bilans de phase 0 et de migration ci-dessous sont des états historiques. Les mentions de phase 1 non commencée ou d'absence de dataset ne décrivent plus le dépôt actuel.

## Bilan précédent — phase 0

## État actuel — 2026-10-23
- Phase : 0 ; tâche : clôture documentaire sur C: ; statut : DONE.
- Phase 1 : non commencée, accord explicite requis.
- Projet officiel : C:\Users\PC\Documents\Projets stage\ecommerce-data-platform.
- Utiliser exclusivement son .venv ; aucun accès ni modification de D:.

## Validation technique — audit du 2026-10-23
- Python 3.11.0 ; interpréteur et préfixe du venv sur C:.
- pip check : No broken requirements found ; pytest : 2 passed in 0.05s.
- Dépendances verrouillées présentes : pytest 9.1.1, colorama 0.4.6, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0 ; outils : pip 22.3, setuptools 65.5.0.
- Espace libre C: : 7,974 Gio à l'audit ; revérifier avant téléchargement ou installation.
- Git : main au commit 7df7e27, aucun écart avec la référence locale origin/main ; aucun fetch exécuté.
- Distant : https://github.com/LaassriaAbdellah/ecommerce-data-platform ; branche backup-local-before-sync présente.
- Working tree propre avant cette mise à jour ; premier commit et synchronisation déjà réalisés.
- Venv, secrets et données ignorés. Aucun dataset ni pipeline métier.
- VS Code : chemin relatif ${workspaceFolder}/.venv/Scripts/python.exe configuré ; sélection effective à confirmer manuellement.
- RAM : 8 Go annoncés, mesure CIM non obtenue. Docker/WSL2/ports restent à vérifier avant services ; aucun service lourd requis pour cette clôture.

## Intervention documentaire — 2026-10-23
- Phase 0 ; tâche : actualiser les trois documents ; statut : DONE.
- Fichiers modifiés : README.md, docs/PROGRESS.md, docs/ARCHITECTURE_DECISIONS.md.
- Résultats Python : audit précédent de ce jour ; pas de nouvelle suite métier pour cette modification.
- Validation documentaire : relecture et git diff --check : aucune erreur (sortie 0).
- Aucun commit, téléchargement, installation, changement de code ou accès à D:.

## Prochaine action
- Confirmer la sélection du venv dans VS Code et la compréhension de la phase 0.
- Après accord pour la phase 1 : préparer l'acquisition des CSV Olist orders, customers et payments, vérifier provenance, conditions et espace requis avant téléchargement, puis proposer le profilage en lecture seule.

## Historique conservé
Les sections suivantes décrivent les états passés. Les mentions de dépendances absentes, de commit en attente ou de reprise sur D: sont remplacées par le bilan ci-dessus. Les preuves des incidents restent conservées sans diagnostic matériel définitif.

## Suivi initial du 2026-10-22

## État actuel
- Phase : 0
- Tâche : initialisation technique de phase 0
- Statut : IN_PROGRESS
- Dernière validation : création et relecture de requirements.txt le 2026-10-22. La phase 0 reste en cours.

## Journal
| Date | Phase | Tâche | Statut | Tests réellement exécutés | Remarques |
|---|---|---|---|---|---|
| 2026-10-22 | 0 | Lecture intégrale d’AGENTS.md et inspection | IN_PROGRESS | Inventaire, git status --short, python --version, py --list-paths, git --version, détection code/docker/wsl, tentative CIM RAM, Get-PSDrive C, exécution du Python de .venv | Python 3.11.0 ; Git 2.47.0 ; Git non initialisé ; .venv fonctionnel (sys.prefix différent de sys.base_prefix) ; py ne trouve aucun Python enregistré. Aucun pytest exécuté. |
| 2026-10-22 | 0 | Vérification des dépendances du .venv, autorisée par « oui continue » | DONE | python -m pip list : pip 22.3 et setuptools 65.5.0 ; python -m pip check : No broken requirements found ; python -m pytest --version : échec, No module named pytest | Commandes exécutées avec .venv/Scripts/python.exe. Aucun paquet installé. Le diagnostic est terminé, mais pytest reste à installer. |

## Fichiers changés
- Création de requirements.txt : déclaration de pytest, sans version verrouillée pour le moment.
- Mise à jour de docs/PROGRESS.md ; environnement .venv existant conservé.

## Prochaine action
- Confirmation de compréhension par l’étudiant et de l’espace disque disponible dans Windows.
- Prochaine petite tâche proposée : vérifier la compatibilité officielle de pytest avec Python 3.11, installer et vérifier pytest, puis verrouiller la version testée dans requirements.txt.

## Blocages / décisions
- RAM : accès CIM refusé ; les 8 Go annoncés restent à vérifier manuellement.
- pytest absent : aucune suite de tests exécutée. pip check valide la cohérence des paquets présents, pas le comportement du projet.
- Certaines commandes ont échoué au lancement à cause du helper ACL de l’environnement ; les vérifications ont pu être relancées séparément sans élévation.
- Disque : Get-PSDrive affiche 0 Gio libres ; valeur à confirmer dans Windows avant installation (mesure potentiellement limitée par l’environnement d’exécution).
- VS Code, Docker et WSL : commandes détectées ; fonctionnement et configuration non vérifiés.
- Ports et WSL2/Docker à vérifier avant installation de services.
- Aucun service lancé, aucune installation, aucune initialisation Git.
- Phase 0 non terminée ; aucune phase suivante sans confirmation explicite.

## Validation de la création de requirements.txt — 2026-10-22
- Phase : 0 ; tâche : création de requirements.txt ; statut : DONE.
- Vérifications exécutées : relecture PowerShell et contrôle que la seule dépendance déclarée est pytest ; contrôle réussi.
- Aucun téléchargement, aucune installation et aucun test pytest exécuté.
- Version non verrouillée : fichier provisoire, reproductibilité des versions à finaliser après installation validée.

## Initialisation phase 0 - 2026-10-22
- Statut : IN_PROGRESS ; preparation technique realisee ; validation et premier commit attendus.
- Crees : src/, tests/, data/, sql/, docker/, .gitignore, .env.example, README.md, docs/ARCHITECTURE_DECISIONS.md ; .gitkeep pour dossiers vides.
- Modifies : requirements.txt verrouille apres tests ; ce suivi. AGENTS.md conserve.
- Installation pytest 9.1.1 et dependances sans cache reussie. pytest -q : 2 passed in 0.03s. pip check : No broken requirements found. pip freeze execute.
- Git initialise ; aucun commit ni ajout index ; git remote -v vide. Exclusions secrets, venv, caches et donnees verifiees avec git check-ignore. .env.example versionnable.
- Python 3.11.0, Git 2.47.0, Docker CLI 29.1.2 (configuration acces refuse). WSL : E_ACCESSDENIED, moteur Docker non valide.
- Disque : 0,23 Gio libres mesures via Python avant installation. RAM non verifiee par CIM (acces refuse).
- Suite : validation et comprehension etudiante, liberer disque manuellement puis approuver premier commit. Phase 1 uniquement apres accord.


## 2026-10-22 - Migration vers D:
- Statut : BLOCKED. Original sur C: conserve ; copie vers D:\DataEngineering\ecommerce-data-platform, NTFS. 30 fichiers verifies SHA256 avant adaptations, aucune difference.
- Nouvel environnement cree sur D:, mais lanceur initial altere et plusieurs dependances contiennent des octets nuls. Lanceur repare depuis modele Python, mais pip check et pytest echouent (ValueError source code string cannot contain null bytes). Aucun test valide sur D:.
- Git copie reconnu, aucun distant/commit ; exclusions verifiees. VS Code ouverture commandee, selection interpreteur a confirmer apres reparation.
- Dossiers datasets et docker-data crees. Docker/WSL non modifies. C: 0,156 Gio, D: 213,721 Gio apres controles.
- Suite : diagnostiquer integrite du support/connexion sans suppression, puis recreer un venv neuf et tester. Ne pas supprimer original ; aucune phase 1.
Diagnostic 2026-10-22 : BLOCKED. enums.py (1619 octets) et pygments/styles/__init__.py (2009) integralement nuls ; references C: sans nul. Scan .py interrompu WinError 1392 : pip/_internal/cli/__pycache__ illisible. chkdsk D: /scan : acces refuse, snapshot error, sortie 1. Test dedie 64 Kio fsync/3 lectures SHA256 OK. Aucune reinstallation, aucun renommage, aucune reparation. Suite : chkdsk /scan en terminal administrateur.
Diagnostic 2026-10-22 : BLOCKED. Deux fichiers integralement nuls : pip/_vendor/chardet/enums.py (1619 octets), pygments/styles/__init__.py (2009). References C: sans nul, SHA256 differents. Scan interrompu WinError 1392 (repertoire pip/_internal/cli/__pycache__ illisible). chkdsk D: /scan : acces refuse, snapshot error, sortie 1. Test 64 Kio fsync/3 lectures SHA256 OK. Aucune reinstallation ni renommage. Suite : chkdsk /scan en PowerShell administrateur.
Preuves : enums.py SHA256 D=478ae5ef84eaf9561c19a6bbbb1fc439f226386a332f56fdc5ed4c64bf13b2ae C=468770e29eb5560f54fa80a8e9e52e4fbb83ccac086c2680d791f06ef0a808d9 ; styles/__init__.py D=7be12613e0282ea3fedac4a4c669127b334af0a349321a7a52de261878f5dc77 C=daf8062a76f2b749dffc248312d3211f1a693d200faf68da7f39791625c5b86b.
Test fichier conserve : .migration-temp/diagnostic-d6b73b8ac1c7469491e7b51ffd8d34aa.bin ; SHA256 d3fa6c28c53e7798df103f2a29bdff780ba81d2fd4fe43fd7594bb23d79b4a00. Lanceur 268152 octets, SHA256 3052784F3683C2BBE95F59560EB311E75F1EAC7AA5476A91BBD9FE4D2AEF880A identique au modele local. Aucun changement des sources, Docker, WSL ou Git.
