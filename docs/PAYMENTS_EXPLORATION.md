# Exploration de Payments — 2026-10-24

## Périmètre et reproduction

Phase 1, exploration uniquement. Notebook créé : notebooks/03_payments_exploration.ipynb. Ouvrir avec le .venv sur C: et exécuter de haut en bas. Code exécuté dans Python pendant l'audit ; fichier notebook sans sorties enregistrées, noyau Jupyter non lancé.

- Python 3.11.0 ; Pandas 3.1.0 déjà installés. Aucune installation ou modification de requirements.txt.
- Espace libre C: à la mesure initiale : 7,102 Gio.
- Source : data/olist_order_payments_dataset.csv ; 5 777 138 octets.
- SHA256 Payments : 4f713964f2815dbbaa40b9488268c55aac3627bfce5aa96cf58d1f3616de3cc0.
- SHA256 Orders : 8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf.
- Sources lues et empreintes comparées avant/après le calcul, sans export ni correction.
- DataFrame Payments seul : 17,815 Mio (memory_usage(deep=True)), pas le pic mémoire du processus. Deux lectures (types inférés et texte), Orders et agrégations consomment aussi de la mémoire ; aucun benchmark.
- Aucun payments_validator.py ni statut valid/review généré.

## Grain et schéma

**103 886 lignes, cinq colonnes, 99 440 commandes distinctes**. Une ligne est un enregistrement de paiement pour une commande ; clé attendue : (order_id, payment_sequential).

| Colonne | Type inféré | Nuls | Vides/espaces |
|---|---|---:|---:|
| order_id | str | 0 | 0 |
| payment_sequential | int64 | 0 | 0 |
| payment_type | str | 0 | 0 |
| payment_installments | int64 | 0 | 0 |
| payment_value | float64 | 0 | 0 |

- Aucun doublon exact excédentaire et aucune ligne impliquée dans un doublon de clé composite.
- Les order_id correspondent tous au format hexadécimal minuscule de 32 caractères ; leur existence dans Orders est vérifiée séparément.
- payment_type ne contient aucun espace de début/fin.
- Aucune date de paiement ni information de devise par ligne dans ce schéma. BRL est la convention du projet pour Olist ; ne pas inventer date d'encaissement, remboursement ou fuseau horaire.
- payment_installments est un compteur d'échéances, distinct de payment_sequential et du nombre de lignes par commande.

## Statistiques descriptives

Les quantiles sont descriptifs et arrondis à quatre décimales ; ils ne deviennent pas des seuils de rejet.

| Mesure | payment_sequential | payment_installments | payment_value (BRL) |
|---|---:|---:|---:|
| Nombre | 103 886 | 103 886 | 103 886 |
| Moyenne | 1,0927 | 2,8533 | 154,1004 |
| Écart-type échantillon | 0,7066 | 2,6871 | 217,4941 |
| Minimum | 1 | 0 | 0 |
| Q1 | 1 | 1 | 56,7900 |
| Médiane | 1 | 1 | 100,0000 |
| Q3 | 1 | 4 | 171,8375 |
| P95 | 1 | 10 | 437,6350 |
| P99 | 3 | 10 | 1 039,9165 |
| Maximum | 29 | 24 | 13 664,08 |

| Contrôle numérique | payment_sequential | payment_installments | payment_value |
|---|---:|---:|---:|
| Manquant | 0 | 0 | 0 |
| Non numérique non nul | 0 | 0 | 0 |
| Non fini non nul | 0 | 0 | 0 |
| Négatif | 0 | 0 | 0 |
| Zéro | 0 | 2 | 9 |
| Fractionnaire fini | 0 | 0 | 99 844 |

Les montants fractionnaires sont normaux. Tous les textes source payment_value suivent un format numérique non négatif à deux décimales au maximum. Les neuf zéros sont des montants renseignés, pas des valeurs manquantes.

Somme descriptive de payment_value : **16 008 872,12 BRL**, calculée exactement avec Decimal à partir des textes source, sur toutes les lignes et tous les statuts. Ce total n'est ni un chiffre d'affaires comptable ni une preuve de paiement encaissé. Ne pas multiplier payment_value par payment_installments.

### Distribution des échéances

| payment_installments | Lignes |
|---|---:|
| 0 | 2 |
| 1 | 52 546 |
| 2 | 12 413 |
| 3 | 10 461 |
| 4 | 7 098 |
| 5 | 5 239 |
| 6 | 3 920 |
| 7 | 1 626 |
| 8 | 4 268 |
| 9 | 644 |
| 10 | 5 328 |
| 11 | 23 |
| 12 | 133 |
| 13 | 16 |
| 14 | 15 |
| 15 | 74 |
| 16 | 5 |
| 17 | 8 |
| 18 | 27 |
| 20 | 17 |
| 21 | 3 |
| 22 | 1 |
| 23 | 1 |
| 24 | 18 |

Les deux valeurs à zéro concernent credit_card. Les 51 338 lignes avec plusieurs échéances concernent aussi credit_card ; les autres types ont payment_installments=1. Zéro demande une investigation, sans imputation automatique à 1. Le maximum observé 24 n'est pas une borne contractuelle validée.

### Distribution des séquences

| payment_sequential | Lignes |
|---|---:|
| 1 | 99 360 |
| 2 | 3 039 |
| 3 | 581 |
| 4 | 278 |
| 5 | 170 |
| 6 | 118 |
| 7 | 82 |
| 8 | 54 |
| 9 | 43 |
| 10 | 34 |
| 11 | 29 |
| 12 | 21 |
| 13 | 13 |
| 14 | 10 |
| 15 | 8 |
| 16 | 6 |
| 17 | 6 |
| 18 | 6 |
| 19 | 6 |
| 20 | 4 |
| 21 | 4 |
| 22 | 3 |
| 23 | 2 |
| 24 | 2 |
| 25 | 2 |
| 26 | 2 |
| 27 | 1 |
| 28 | 1 |
| 29 | 1 |

## Types de paiement

| Type observé | Lignes | Part des lignes | Montants zéro |
|---|---:|---:|---:|
| credit_card | 76 795 | 73,9224 % | 0 |
| boleto | 19 784 | 19,0440 % | 0 |
| voucher | 5 775 | 5,5590 % | 6 |
| debit_card | 1 529 | 1,4718 % | 0 |
| not_defined | 3 | 0,0029 % | 3 |

- not_defined est une valeur explicite présente, pas un null : trois lignes, toutes à montant zéro.
- Six montants zéro sont associés à voucher ; aucun à credit_card, boleto ou debit_card.
- Ne pas renommer ni supprimer ces valeurs sans règle métier validée. Les cinq catégories sont observées ; une liste fermée future nécessitera une politique pour les nouvelles catégories.

## Paiements multiples et clé composite

- **2 961 commandes** ont plusieurs lignes de paiement, soit 7 407 lignes concernées.
- 96 479 commandes ont une seule ligne ; 4 446 répétitions excédentaires de order_id sont normales.
- Maximum : 29 lignes pour une commande, pas 29 échéances nécessairement.
- 2 246 commandes combinent plusieurs payment_type ; paiements multiples et types multiples ne sont pas équivalents.
- 80 commandes ont une séquence dont le minimum n'est pas 1. Aucun trou interne entre minimum et maximum et aucune clé dupliquée détectés.
- Ne pas imposer que chaque séquence commence à 1 : une numérotation inhabituelle ne prouve ni duplication ni perte sans contrat source.
- Ne pas imposer l'unicité de order_id seul.

## Références Orders et complétude

Jointure Payments → Orders avec validate="many_to_one", sans jointure avec Order Items :
- Orders : 99 441 lignes, aucune clé order_id dupliquée.
- Jointure : 103 886 lignes conservées ; **aucune référence inconnue**.
- **Une commande delivered sans paiement enregistré**. C'est un signal de complétude à examiner côté Orders, pas une ligne Payments à signaler puisqu'elle n'existe pas.
- Les neuf lignes à montant zéro concernent huit commandes : quatre lignes delivered, trois canceled, deux shipped.
- Trois commandes ont une somme de paiements nulle. Ne pas assimiler automatiquement ces cas à une erreur comptable ou à un remboursement.
- Aucun rapprochement monétaire Items/Payments exécuté. Une éventuelle comparaison future doit agréger séparément les deux tables au grain order_id avant jointure ; ne jamais sommer après une jointure directe items × payments.

## Règles structurelles proposées — accord requis

Aucune règle ci-dessous n'est implémentée pendant cette exploration.

1. Schéma : les cinq colonnes obligatoires ; check_required_columns() existant.
2. order_id requis et non vide ; check_missing_ids(). Référence à une commande existante ; exclure un ID absent du motif unknown_order pour éviter le double signalement.
3. payment_sequential numérique, fini, entier et strictement positif ; pas de maximum arbitraire.
4. Clé (order_id, payment_sequential) unique : signaler toutes les lignes impliquées. Normaliser le compteur pour comparer 1 et "1", sans modifier le brut. Le helper check_duplicate_ids() accepte une sélection composite ; exclure les clés incomplètes/invalides du motif de doublon.
5. payment_type requis et non vide ; catalogue proposé : credit_card, boleto, voucher, debit_card, not_defined. Signaler une catégorie inconnue, mais conserver not_defined dans le contrat initial et comme indicateur métier.
6. payment_installments numérique, fini et entier >=0 ; zéro autorisé structurellement dans cette proposition et signalé séparément. Une contrainte >0 doit faire l'objet d'une décision explicite après investigation des deux lignes.
7. payment_value numérique, fini et >=0 ; zéro autorisé structurellement et suivi séparément. Un futur montant négatif serait à examiner sans l'interpréter automatiquement comme remboursement.
8. Les valeurs booléennes ne doivent pas être acceptées comme compteurs/montants. Les montants décimaux sont autorisés.

Ces règles reprennent les conventions du moteur de qualité : motifs précis, comptage des lignes une seule fois dans review, aucune suppression ou correction. Aucune définition de statut de validation global pour ce fichier n'est annoncée avant implémentation.

## Indicateurs métier séparés proposés

- Montants zéro (9 lignes / 8 commandes), sommes par commande nulles (3), types not_defined (3) et échéances zéro (2).
- Paiements multiples (2 961 commandes), types combinés (2 246), séquences ne commençant pas à 1 (80).
- Distribution et extrêmes des montants, compteurs et types ; pas de borne arbitraire au maximum observé.
- Complétude côté Orders : une commande delivered sans paiement ; analyser sa provenance/statut avant correction.
- Sommes par commande et type, calculées sans multiplier par les échéances et sans déduire un chiffre d'affaires comptable.
- Aucun KPI de fraîcheur/retard de paiement sans date de paiement documentée.

## Vérifications et suite
- Suite existante exécutée : .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider ; **90 passed in 3.70s**.
- pip check : No broken requirements found.
- Contrôles finaux : code enregistré du notebook exécuté dans Python, résultat identique au premier calcul ; SHA256 de 29 fichiers protégés inchangés (données, validateurs, tests et anciens notebooks) ; git diff --check sans erreur. Les fichiers de pipeline Payments restent absents.
- Aucun validateur, helper, test ou CSV modifié ; aucune nouvelle sortie de pipeline. Aucun téléchargement, installation, service lourd, commit/push ou accès à D:.
- Faire valider la politique des zéros, de not_defined et des séquences avant de développer Payments. Phase 1 reste en cours.
