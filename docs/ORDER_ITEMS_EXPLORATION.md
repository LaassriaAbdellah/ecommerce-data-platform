# Exploration de order_items — 2026-10-24

## Périmètre et reproduction
- Phase 1, exploration en lecture seule. Aucun validateur order_items créé.
- Python 3.11.0 du .venv sur C:, Pandas 3.1.0, ipykernel 7.4.0 déjà installés ; ajout des deux versions à requirements.txt car absentes. Métadonnées locales Requires-Python >=3.11 pour chacun : compatibles avec Python utilisé.
- Espace libre mesuré : 7,151 Gio. Aucun téléchargement ou service démarré.
- Notebook reproductible : notebooks/02_order_items_exploration.ipynb, sans sorties enregistrées. Code exécuté avec le Python local pour cet audit ; noyau Jupyter non lancé. Ouvrir le notebook et sélectionner le .venv pour le reproduire.
- Fichier analysé : data/olist_order_items_dataset.csv, 15 438 671 octets.
- SHA256 items : 0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279.
- SHA256 orders : 8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf.
- Empreintes de ces deux sources comparées avant/après le calcul : identiques.
- DataFrame items seul : 39,427 Mio selon memory_usage(deep=True). Ce n'est pas la mémoire totale ni le pic du processus : la lecture texte, orders et les jointures consomment aussi de la mémoire. Aucun benchmark de performance.

## Schéma et complétude

112 650 lignes, 7 colonnes ; grain attendu : une ligne d'article par couple (order_id, order_item_id).

| Colonne | Type inféré par Pandas 3.1 | Valeurs nulles | Chaînes vides/espaces |
|---|---|---:|---:|
| order_id | str | 0 | 0 |
| order_item_id | int64 | 0 | 0 |
| product_id | str | 0 | 0 |
| seller_id | str | 0 | 0 |
| shipping_limit_date | str | 0 | 0 |
| price | float64 | 0 | 0 |
| freight_value | float64 | 0 | 0 |

Les trois identifiants texte correspondent tous au format hexadécimal minuscule de 32 caractères. Format observé, pas preuve de référence valide à une autre table.

- Doublons exacts excédentaires : 0.
- Lignes impliquées dans un doublon de clé composite : 0.
- order_id distincts : 98 666 ; 13 984 répétitions excédentaires de order_id sont normales au grain article.
- 9 803 commandes contiennent plusieurs lignes ; maximum observé : 21 lignes par commande.
- Aucune commande avec séquence order_item_id discontinue, départ différent de 1 ou identifiant répété.
- 32 951 produits et 3 095 vendeurs distincts. Leurs références aux tables products/sellers n'ont pas été vérifiées dans cette mission.

## Statistiques numériques

Montants en BRL, observations descriptives, sans seuil de suppression.

| Mesure | order_item_id | price | freight_value |
|---|---:|---:|---:|
| Nombre | 112 650 | 112 650 | 112 650 |
| Moyenne | 1,1978 | 120,6537 | 19,9903 |
| Écart-type échantillon | 0,7051 | 183,6339 | 15,8064 |
| Minimum | 1 | 0,85 | 0 |
| Q1 | 1 | 39,90 | 13,08 |
| Médiane | 1 | 74,99 | 16,26 |
| Q3 | 1 | 134,90 | 21,15 |
| P95 | 2 | 349,90 | 45,12 |
| P99 | 4 | 890 | 84,52 |
| Maximum | 21 | 6 735 | 409,68 |

- Aucun nombre non convertible, nul, infini ou négatif dans les trois colonnes.
- price : aucun zéro. freight_value : 383 zéros ; compatibles avec des frais nuls, ne pas les signaler automatiquement comme invalides.
- order_item_id : aucun zéro ni nombre fractionnaire.
- Les montants fractionnaires sont normaux ; aucun montant source hors du format numérique observé à deux décimales au maximum.
- 21 articles, 6 735 BRL ou 409,68 BRL sont des extrêmes observés, pas des bornes métier justifiées.
- Les floats conviennent au profilage ; pour une future réconciliation financière exacte, définir Decimal ou centimes entiers. Ne pas assimiler sommes des articles et chiffre d'affaires comptable.

## Dates et liens avec orders

shipping_limit_date suit partout YYYY-MM-DD HH:MM:SS ; conversion stricte avec format explicite : aucune date absente, mal formée ou impossible. Dates sans fuseau explicite ; aucune conversion UTC inventée.

- Minimum : 2016-09-19 00:15:34 ; maximum : 2020-04-09 22:35:08.
- Répartition par année : 2016 : 370 ; 2017 : 49 765 ; 2018 : 62 511 ; 2020 : 4.
- Écart échéance - achat : min 2,0042 jours ; médiane 6,0120 ; P95 12,0304 ; P99 19,0077 ; max 1 056,0417 jours.
- Les quatre dates en 2020 et l'écart maximal sont à examiner ; aucune correction ni date limite arbitraire choisie.

Jointure items → orders avec validate="many_to_one" : order_id est unique dans les 99 441 lignes orders, et la jointure conserve exactement 112 650 lignes. Aucune multiplication de lignes. Aucune jointure items × payments.

| Contrôle relationnel/chronologique | Lignes items | Commandes distinctes |
|---|---:|---:|
| Référence order_id inconnue | 0 | 0 |
| Échéance avant achat | 0 | 0 |
| Échéance avant approbation | 127 | 116 |
| Remise réelle au transporteur après échéance | 10 423 | 8 861 |

shipping_limit_date représente une échéance, pas une remise réelle au transporteur. Une échéance avant approbation est un signal d'investigation ; une remise après échéance est un retard potentiel, pas nécessairement une incohérence de saisie. Comparaisons uniquement lorsque les deux dates existent ; une comparaison avec une date manquante ne devient pas une absence d'anomalie garantie.

775 commandes de orders n'ont aucune ligne dans items :
- unavailable : 603 ; canceled : 164 ; created : 5 ; invoiced : 2 ; shipped : 1.
- Aucune commande delivered sans article dans ce contrôle.
- L'absence d'article peut être cohérente pour unavailable/canceled. Les autres statuts demandent une investigation, notamment shipped. C'est un contrôle de complétude côté orders, pas un motif à attribuer à une ligne items inexistante.

## Règles proposées — non implémentées, validation requise

Contrat structurel :
1. Vérifier les sept colonnes obligatoires ; erreur explicite si le schéma est incomplet (check_required_columns existant).
2. Signaler les order_id, product_id et seller_id nuls, vides ou composés d'espaces (check_missing_ids existant).
3. Signaler order_item_id manquant, non numérique, non fini, non entier ou inférieur à 1. Ne pas imposer 21 comme maximum.
4. Vérifier l'unicité du couple (order_id, order_item_id), en marquant toutes les lignes impliquées. Le helper check_duplicate_ids actuel ne gère qu'une colonne ; ne pas l'appliquer à order_id seul. Définir le traitement des clés incomplètes avant implémentation.
5. Vérifier que chaque order_id non vide existe dans orders. Ne pas joindre sur une clé orders dupliquée sans erreur explicite.
6. Signaler price manquant, non numérique, non fini ou <= 0 (prix nul à considérer comme suspect, politique métier à confirmer).
7. Signaler freight_value manquant, non numérique, non fini ou < 0 ; autoriser 0.
8. Signaler shipping_limit_date manquante/non convertible ; format source explicite. Le helper check_invalid_dates peut contribuer, mais le contrat de format doit être décidé.

Contrôles d'investigation à distinguer du contrat :
- Proposer shipping_limit_before_purchase comme motif chronologique ; aucun cas présent.
- Examiner les 127 lignes avant approbation et les quatre dates en 2020 avant de décider d'un motif review ou d'une métrique. Aucun seuil arbitraire de délai ou de montant.
- Conserver les retards transporteur après échéance comme indicateur opérationnel, sans confondre retard et corruption.
- Rapporter les séquences discontinues à l'échelle commande si la convention 1..N est confirmée ; zéro cas observé ici.
- Vérifier products/sellers ultérieurement si ce périmètre est autorisé.
- Produire les trois colonnes et le rapport via apply_quality_rules() seulement après accord. Aucun fichier orders/customers existant modifié.

## Vérifications réalisées
- pip check : No broken requirements found.
- Suite existante : 21 passed in 1.20s, via .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider.
- Aucune nouvelle règle de validateur ni test métier ajouté. Aucun CSV source ou dérivé réécrit ; aucun commit/push.

- Contrôle final : 23 fichiers protégés comparés par SHA256, inchangés (sources, sorties existantes, validateurs et tests). Code enregistré du nouveau notebook exécuté avec succès dans Python, sans sauvegarder de sorties notebook. git diff --check sans erreur.
