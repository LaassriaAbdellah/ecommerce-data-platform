# Exploration de Products — 2026-10-24

## Périmètre et reproduction

Phase 1, exploration uniquement. Aucun products_validator.py ni sortie de pipeline Products créé. Pas de statut valid/review attribué aux produits à cette étape.

- Notebook : notebooks/04_products_exploration.ipynb, conforme aux conventions précédentes (Path, Pandas, jointures contrôlées, lecture seule).
- Exécuter de haut en bas depuis la racine ou notebooks/ avec le .venv sur C:. Le code a été exécuté avec Python pendant l'audit ; notebook livré sans sorties enregistrées, sans lancement de noyau Jupyter.
- Python 3.11.0, Pandas 3.1.0 déjà installés ; 5,532 Gio libres sur C: à la mesure initiale. Aucun paquet installé.
- Source Products : 2 379 446 octets ; DataFrame seul : 6,795 Mio selon memory_usage(deep=True), pas le pic mémoire du processus. Les autres lectures et jointures consomment aussi de la mémoire.
- Sources examinées : Products, product_id d'Order Items et product_category_name_translation.csv. Aucun CSV réécrit.

| Source | SHA256 |
|---|---|
| olist_products_dataset.csv | 3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc |
| olist_order_items_dataset.csv | 0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279 |
| product_category_name_translation.csv | a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278 |

Ces empreintes sont vérifiées avant/après le calcul exploratoire.

## Dimensions, types et valeurs manquantes

**32 951 lignes, neuf colonnes, 32 951 product_id distincts.** Grain attendu : une ligne par produit.

Les noms source product_name_lenght et product_description_lenght contiennent bien cette orthographe ; ils ne sont pas renommés. Ces colonnes sont des longueurs déclarées : les textes des noms/descriptions ne sont pas dans Products, donc leur longueur réelle ne peut pas être recalculée ici.

| Colonne | Type inféré | Nuls Pandas | Part manquante | Champs source vides/espaces |
|---|---|---:|---:|---:|
| `product_id` | str | 0 | 0 % | 0 |
| `product_category_name` | str | 610 | 1,8512 % | 610 |
| `product_name_lenght` | float64 | 610 | 1,8512 % | 610 |
| `product_description_lenght` | float64 | 610 | 1,8512 % | 610 |
| `product_photos_qty` | float64 | 610 | 1,8512 % | 610 |
| `product_weight_g` | float64 | 2 | 0,0061 % | 2 |
| `product_length_cm` | float64 | 2 | 0,0061 % | 2 |
| `product_height_cm` | float64 | 2 | 0,0061 % | 2 |
| `product_width_cm` | float64 | 2 | 0,0061 % | 2 |

Les champs vides sont les mêmes observations que les valeurs manquantes après lecture Pandas, pas un second ensemble à additionner. Aucune chaîne non vide composée seulement d'espaces et aucun espace autour des catégories détectés.

Les sept champs numériques sont float64 en raison des manques, même lorsque leurs valeurs renseignées sont intégrales ; ce type n'est pas une anomalie.

- Aucun doublon exact excédentaire et aucune ligne impliquée dans un doublon de product_id.
- Aucun identifiant absent/vide et aucun écart au format hexadécimal minuscule de 32 caractères.
- 610 produits ont simultanément catégorie, longueur de nom, longueur de description et nombre de photos absents.
- Deux produits ont simultanément poids et trois dimensions absents.
- Un produit appartient aux deux groupes : **611 produits ont au moins un manque**, pas 612 ni une somme des nulls par colonne.
- Ne pas inventer de catégorie, longueur, photo ou mesure pour combler ces manques.

## Statistiques descriptives numériques

Statistiques sur les valeurs renseignées. Moyennes, écarts-types échantillon et quantiles arrondis à quatre décimales. Poids en grammes ; dimensions en centimètres ; longueurs de texte et photos sont des compteurs.

| Colonne | Nombre renseigné | Moyenne | Écart-type | Min | Q1 | Médiane | Q3 | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `product_name_lenght` | 32 341 | 48,4769 | 10,2457 | 5 | 42 | 51 | 57 | 60 | 63 | 76 |
| `product_description_lenght` | 32 341 | 771,4953 | 635,1152 | 4 | 339 | 595 | 972 | 2 063 | 3 286,2 | 3 992 |
| `product_photos_qty` | 32 341 | 2,189 | 1,7368 | 1 | 1 | 1 | 3 | 6 | 8 | 20 |
| `product_weight_g` | 32 949 | 2 276,4725 | 4 282,0387 | 0 | 300 | 700 | 1 900 | 10 850 | 22 538 | 40 425 |
| `product_length_cm` | 32 949 | 30,8151 | 16,9145 | 7 | 18 | 25 | 38 | 65 | 100 | 105 |
| `product_height_cm` | 32 949 | 16,9377 | 13,6376 | 2 | 8 | 13 | 21 | 44 | 69 | 105 |
| `product_width_cm` | 32 949 | 23,1967 | 12,079 | 6 | 15 | 20 | 30 | 47 | 63 | 118 |

| Colonne | Manquant | Non numérique non nul | Infini non nul | Négatif | Zéro | Fractionnaire fini |
|---|---:|---:|---:|---:|---:|---:|
| `product_name_lenght` | 610 | 0 | 0 | 0 | 0 | 0 |
| `product_description_lenght` | 610 | 0 | 0 | 0 | 0 | 0 |
| `product_photos_qty` | 610 | 0 | 0 | 0 | 0 | 0 |
| `product_weight_g` | 2 | 0 | 0 | 0 | 4 | 0 |
| `product_length_cm` | 2 | 0 | 0 | 0 | 0 | 0 |
| `product_height_cm` | 2 | 0 | 0 | 0 | 0 | 0 |
| `product_width_cm` | 2 | 0 | 0 | 0 | 0 | 0 |

- Aucun nombre renseigné non convertible, infini, négatif ou fractionnaire dans ce fichier.
- Les NaN provenant de champs absents sont comptés comme manques, pas comme valeurs infinies.
- Quatre poids valent zéro ; aucune dimension, longueur descriptive ou quantité de photos renseignée ne vaut zéro.
- Poids maximal : 40 425 g ; dimensions maximales : 105 × 105 × 118 cm prises séparément par colonne. Ces maxima ne décrivent pas nécessairement un même produit.
- Description maximale : 3 992 ; nombre de photos maximal : 20. Ce sont des valeurs observées, pas des limites métier autorisées.
- Les dimensions/poids présents sont entiers dans cet échantillon ; ne pas en déduire que des mesures fractionnaires futures seraient invalides.
- Poids nul et extrêmes nécessitent une investigation de contexte ; aucun produit supprimé, corrigé ou classé automatiquement en erreur.

## Distribution des catégories

73 catégories renseignées distinctes ; 610 produits sans catégorie (1,8512 %). Les pourcentages ci-dessous prennent les **32 951 produits** comme dénominateur, manques inclus. Ce sont des fréquences de produits distincts, pas des ventes, des lignes d'article ni du chiffre d'affaires.

| Catégorie source | Produits | Part de tous les produits |
|---|---:|---:|
| `cama_mesa_banho` | 3 029 | 9,1924 % |
| `esporte_lazer` | 2 867 | 8,7008 % |
| `moveis_decoracao` | 2 657 | 8,0635 % |
| `beleza_saude` | 2 444 | 7,4171 % |
| `utilidades_domesticas` | 2 335 | 7,0863 % |
| `automotivo` | 1 900 | 5,7661 % |
| `informatica_acessorios` | 1 639 | 4,9741 % |
| `brinquedos` | 1 411 | 4,2821 % |
| `relogios_presentes` | 1 329 | 4,0333 % |
| `telefonia` | 1 134 | 3,4415 % |
| `bebes` | 919 | 2,789 % |
| `perfumaria` | 868 | 2,6342 % |
| `papelaria` | 849 | 2,5766 % |
| `fashion_bolsas_e_acessorios` | 849 | 2,5766 % |
| `cool_stuff` | 789 | 2,3945 % |
| `ferramentas_jardim` | 753 | 2,2852 % |
| `pet_shop` | 719 | 2,182 % |
| `eletronicos` | 517 | 1,569 % |
| `construcao_ferramentas_construcao` | 400 | 1,2139 % |
| `eletrodomesticos` | 370 | 1,1229 % |
| `malas_acessorios` | 349 | 1,0591 % |
| `consoles_games` | 317 | 0,962 % |
| `moveis_escritorio` | 309 | 0,9378 % |
| `instrumentos_musicais` | 289 | 0,8771 % |
| `eletroportateis` | 231 | 0,701 % |
| `casa_construcao` | 225 | 0,6828 % |
| `livros_interesse_geral` | 216 | 0,6555 % |
| `fashion_calcados` | 173 | 0,525 % |
| `moveis_sala` | 156 | 0,4734 % |
| `climatizacao` | 124 | 0,3763 % |
| `livros_tecnicos` | 123 | 0,3733 % |
| `telefonia_fixa` | 116 | 0,352 % |
| `casa_conforto` | 111 | 0,3369 % |
| `market_place` | 104 | 0,3156 % |
| `alimentos_bebidas` | 104 | 0,3156 % |
| `fashion_roupa_masculina` | 95 | 0,2883 % |
| `moveis_cozinha_area_de_servico_jantar_e_jardim` | 94 | 0,2853 % |
| `sinalizacao_e_seguranca` | 93 | 0,2822 % |
| `construcao_ferramentas_seguranca` | 91 | 0,2762 % |
| `eletrodomesticos_2` | 90 | 0,2731 % |
| `construcao_ferramentas_jardim` | 88 | 0,2671 % |
| `alimentos` | 82 | 0,2489 % |
| `bebidas` | 81 | 0,2458 % |
| `construcao_ferramentas_iluminacao` | 78 | 0,2367 % |
| `agro_industria_e_comercio` | 74 | 0,2246 % |
| `industria_comercio_e_negocios` | 68 | 0,2064 % |
| `artigos_de_natal` | 65 | 0,1973 % |
| `audio` | 58 | 0,176 % |
| `artes` | 55 | 0,1669 % |
| `fashion_underwear_e_moda_praia` | 53 | 0,1608 % |
| `dvds_blu_ray` | 48 | 0,1457 % |
| `moveis_quarto` | 45 | 0,1366 % |
| `construcao_ferramentas_ferramentas` | 39 | 0,1184 % |
| `livros_importados` | 31 | 0,0941 % |
| `portateis_casa_forno_e_cafe` | 31 | 0,0941 % |
| `pcs` | 30 | 0,091 % |
| `cine_foto` | 28 | 0,085 % |
| `fashion_roupa_feminina` | 27 | 0,0819 % |
| `musica` | 27 | 0,0819 % |
| `artigos_de_festas` | 26 | 0,0789 % |
| `fashion_esporte` | 19 | 0,0577 % |
| `artes_e_artesanato` | 19 | 0,0577 % |
| `flores` | 14 | 0,0425 % |
| `fraldas_higiene` | 12 | 0,0364 % |
| `la_cuisine` | 10 | 0,0303 % |
| `portateis_cozinha_e_preparadores_de_alimentos` | 10 | 0,0303 % |
| `moveis_colchao_e_estofado` | 10 | 0,0303 % |
| `tablets_impressao_imagem` | 9 | 0,0273 % |
| `fashion_roupa_infanto_juvenil` | 5 | 0,0152 % |
| `casa_conforto_2` | 5 | 0,0152 % |
| `pc_gamer` | 3 | 0,0091 % |
| `seguros_e_servicos` | 2 | 0,0061 % |
| `cds_dvds_musicais` | 1 | 0,003 % |
| Catégorie manquante | 610 | 1,8512 % |

Les catégories rares restent des valeurs observées. Aucune liste fermée de 73 catégories imposée comme contrat futur.

## Relations avec Order Items

Jointure items → products avec validate="many_to_one", sans perte ni multiplication :
- 112 650 lignes Order Items ; 32 951 product_id distincts.
- Jointure : 112 650 lignes ; **aucune référence product_id inconnue** (ni ligne ni identifiant distinct).
- **Aucun produit non référencé dans Order Items** : les 32 951 produits y apparaissent.
- Cette observation ne signifie pas qu'un produit sans vente serait invalide dans un futur catalogue ; c'est un indicateur d'usage.
- Les produits sans catégorie concernent 1 603 lignes d'article ; les produits sans données physiques concernent 18 lignes d'article.
- Ne pas confondre 610 produits sans catégorie et 1 603 articles concernés, ni compter les lignes items comme des produits distincts.

## Correspondance des catégories avec la traduction

La table product_category_name_translation.csv contient **71 lignes et deux colonnes** :
- product_category_name ;
- product_category_name_english.

Aucune valeur manquante/vide, aucun doublon exact ou doublon de catégorie source. La jointure de traduction conserve 32 951 produits avec validate="many_to_one". Les 71 catégories traduites sont toutes présentes dans Products.

Deux catégories non nulles n'ont pas de traduction :

| Catégorie | Produits |
|---|---:|
| pc_gamer | 3 |
| portateis_cozinha_e_preparadores_de_alimentos | 10 |

Cela représente **13 produits et 24 lignes Order Items**. À distinguer des 610 catégories absentes : 32 328 produits ont une catégorie traduite, 13 une catégorie renseignée non traduite et 610 aucune catégorie.

Une absence de correspondance peut révéler une couverture incomplète du fichier de traduction. Elle ne prouve pas que le produit ou son libellé portugais est invalide. Aucun libellé anglais ou rapprochement approximatif inventé ; pas de modification de la table de correspondance.

## Proposition de contrat structurel — à valider

Aucune règle de validateur n'est implémentée par cet audit.

1. Les neuf colonnes doivent exister : check_required_columns() existant. Présence de la colonne obligatoire ne signifie pas que chaque valeur est obligatoire.
2. product_id requis, non vide et unique, avec check_missing_ids() et check_duplicate_ids(). Signaler toutes les occurrences d'un ID dupliqué sans supprimer de ligne ; exclure les IDs absents du motif de doublon.
3. Pour les sept colonnes numériques **lorsqu'elles sont renseignées** : valeurs convertibles, finies et non négatives ; refuser les booléens. Les manques restent autorisés par la politique proposée, avec indicateurs de complétude séparés.
4. product_name_lenght, product_description_lenght et product_photos_qty : valeurs renseignées entières >=0. Pas de maximum arbitraire ; zéro éventuel suivi séparément selon le contexte.
5. product_weight_g et dimensions : valeurs renseignées finies >=0 dans le contrat initial proposé ; mesures décimales admises. Les zéros, notamment quatre poids observés, deviennent des indicateurs d'investigation, sans présumer une erreur. Une exigence >0 éventuelle devra être décidée explicitement.
6. product_category_name peut être absente ; pas de valeur artificielle « unknown » écrite dans le brut, ni rejet parce qu'une traduction manque. Séparer « catégorie absente » et « catégorie renseignée non traduite ».
7. Vérifier la référence Item → Product dans les contrôles inter-tables ; ne pas utiliser l'absence de vente d'un produit comme défaut structurel.
8. Réutiliser le moteur pour les trois colonnes de qualité seulement après validation de ce contrat. Les erreurs structurelles potentielles et indicateurs ne doivent pas être mélangés.

L'observation de champs manquants n'est pas une preuve qu'ils sont toujours autorisés : il s'agit ici d'une proposition explicite à confirmer avec l'étudiant, compatible avec la conservation des données sources et l'absence de contexte métier plus précis.

## Indicateurs métier/completude proposés, séparés des erreurs

| Indicateur | Grain | Observation |
|---|---|---:|
| Catégorie absente | produit | 610 |
| Métadonnées descriptives absentes | produit | 610 |
| Poids/dimensions absents | produit | 2 |
| Au moins un champ absent | produit | 611 |
| Poids égal à zéro | produit | 4 |
| Catégorie présente non traduite | produit | 13 |
| Catégorie présente non traduite | catégorie distincte | 2 |
| Produit non référencé dans Items | produit | 0 |
| Référence produit inconnue | ligne Item | 0 |

Ces indicateurs peuvent se chevaucher et ne s'additionnent pas pour produire un nombre de produits distincts. Poids nul, catégorie inconnue de la traduction et valeurs extrêmes demandent un examen ; aucune correction automatique, aucune borne universelle sur les dimensions/poids ou les longueurs.

## Vérifications et prochaine action
- .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider : **166 passed in 3.97s**.
- .venv/Scripts/python.exe -B -m pip check : No broken requirements found.
- Contrôles finaux : code enregistré du notebook exécuté dans Python, résultat identique au premier calcul ; SHA256 des 34 fichiers protégés inchangés (données, sorties, code/tests et anciens notebooks) ; git diff --check sans erreur. Validateur et sorties Products absents.
- Fichiers de cette intervention : création du notebook 04 et de ce rapport, mise à jour de docs/PROGRESS.md uniquement.
- Aucun CSV source, sortie dérivée, validateur, helper, test ou ancien notebook modifié ; aucun téléchargement, installation, commit/push, service lourd ou accès à D:.
- Faire valider la politique des champs optionnels et des zéros avant tout products_validator.py. Aucun autre dataset ni phase suivante commencé.
