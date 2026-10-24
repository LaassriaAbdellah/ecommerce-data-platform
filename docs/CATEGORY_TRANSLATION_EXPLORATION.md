# Exploration de Category Translation — 2026-10-24

## Périmètre et reproduction

Phase 1, exploration uniquement de product_category_name_translation.csv et de ses relations avec Products. Aucun neuvième validateur ou fichier de sortie créé, aucun statut valid/review attribué, aucune traduction ajoutée.

Notebook : [08_category_translation_exploration.ipynb](../notebooks/08_category_translation_exploration.ipynb). Exécuter de haut en bas depuis la racine ou notebooks/, avec le .venv du projet sur C:. Conventions Path/Pandas, SHA256, jointure contrôlée et séparation des indicateurs reprises des explorations précédentes.

Python 3.11.0, Pandas 3.1.0 déjà présents ; espace libre initial C: 3,137 Gio ; source de traduction de 2 613 octets. Aucun téléchargement/installation ni service lourd. Products lu avec product_id et product_category_name seulement.

Le code enregistré du notebook a été exécuté avec Python, sans noyau Jupyter ; sorties du notebook laissées vides. Empreintes vérifiées avant/après le calcul :

| Source | SHA256 |
|---|---|
| product_category_name_translation.csv | a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278 |
| olist_products_dataset.csv | 3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc |

## Schéma et complétude

**71 lignes, deux colonnes.** Grain observé : une correspondance par catégorie portugaise.

| Colonne | Type inféré Pandas | Nuls | Chaînes vides | Espaces seuls |
|---|---|---:|---:|---:|
| product_category_name | str | 0 | 0 | 0 |
| product_category_name_english | str | 0 | 0 | 0 |

La lecture complémentaire dtype="string", keep_default_na=False permet de distinguer les champs source vides des nulls du parseur. Aucun doublon complet : zéro occurrence excédentaire et zéro ligne impliquée.

## Cardinalités et ambiguïtés

| Contrôle | Résultat |
|---|---:|
| Catégories portugaises distinctes | 71 |
| Catégories portugaises dupliquées | 0 |
| Libellés anglais distincts | 71 |
| Libellés anglais répétés | 0 |
| Catégories portugaises avec plusieurs traductions anglaises non vides | 0 |
| Libellés anglais partagés par plusieurs catégories portugaises | 0 |

La correspondance est un-à-un **dans cet échantillon**. Le contrat doit cependant distinguer les deux sens :
- Une catégorie portugaise doit désigner une correspondance unique pour permettre une jointure many_to_one fiable.
- Plusieurs catégories portugaises peuvent partager un même libellé anglais sans rendre la jointure portugais → anglais ambiguë.
- Une contradiction signifie plusieurs libellés anglais distincts non vides pour une même catégorie portugaise exacte.
- Un doublon exact de correspondance ne constitue pas une contradiction linguistique, mais viole tout de même l'unicité proposée de la clé portugaise.

Aucune unicité anglaise n'est proposée simplement parce qu'elle est observée ici. Les contrôles structurels ne peuvent pas prouver l'exactitude linguistique des traductions.

## Écriture et caractères

Pour chacune des deux colonnes : zéro espace en bordure, espace intérieur, caractère non ASCII, majuscule ou écart au motif descriptif [a-z0-9]+(?:_[a-z0-9]+)*.

Les variantes potentielles sont recherchées par casefold, NFKD, retrait des accents, remplacement des caractères non alphanumériques par un underscore et retrait des underscores de bordure. **Aucun groupe de collision normalisée** détecté. Cette clé reste exploratoire et n'est jamais écrite dans les sources.

Les suffixes numériques observés sont :
- eletrodomesticos_2 → home_appliances_2 ;
- casa_conforto_2 → home_comfort_2.

Ils ne sont pas considérés comme des erreurs. Le motif de libellé, l'ASCII ou l'absence d'accent ne deviennent pas des contraintes de rejet supplémentaires sans décision métier.

## Relations avec Products

Products contient **32 951 produits**, **73 catégories renseignées distinctes** et **610 produits sans catégorie**. Les catégories absentes ne sont pas assimilées à des catégories connues dépourvues de traduction.

| Catégorie utilisée sans traduction | Produits | Lignes de traduction |
|---|---:|---:|
| pc_gamer | 3 | 0 |
| portateis_cozinha_e_preparadores_de_alimentos | 10 | 0 |
| Total | 13 | 0 |

Ces deux catégories sont absentes de la table source ; aucune traduction n'a été inventée ni ajoutée.

| Mesure | Résultat |
|---|---:|
| Produits avec catégorie renseignée et traduite | 32 328 |
| Produits avec catégorie renseignée sans traduction | 13 |
| Produits sans catégorie | 610 |
| Catégories traduites mais inutilisées dans Products | 0 |
| Produits sur une correspondance contradictoire | 0 |
| Lignes après jointure gauche many_to_one | 32 951 |
| Lignes sans correspondance, catégorie absente incluse | 623 |

Les trois premiers groupes sont disjoints : 32 328 + 13 + 610 = 32 951. Le total de 623 lignes sans correspondance comprend **13 catégories renseignées non traduites et 610 catégories absentes** ; il ne doit pas être présenté comme 623 produits avec une catégorie connue non traduite.

Les 71 catégories de la table sont toutes utilisées dans Products. La jointure conserve le nombre de produits, sans multiplication. Le notebook bloque cette jointure de démonstration si la catégorie portugaise est dupliquée dans le fichier, plutôt que de sélectionner arbitrairement une correspondance.

## Contrat de validation proposé — en attente de validation

| Contrôle structurel | Politique proposée |
|---|---|
| Deux colonnes obligatoires | Conserver les noms source |
| Catégorie portugaise renseignée et non vide | Null, vide et espaces seuls considérés absents |
| Traduction anglaise renseignée et non vide | Ne pas inventer de valeur de remplacement |
| Catégorie portugaise unique | Signaler toutes les occurrences impliquées |
| Traductions contradictoires pour une catégorie portugaise | Contrôle explicite sur les traductions distinctes renseignées |

Un doublon de catégorie et une contradiction peuvent toucher les mêmes lignes : les compteurs par règle se chevauchent, mais une ligne à examiner ne se compte qu'une fois. Les clés manquantes doivent avoir leur propre motif, sans doublon artificiel entre absences.

Indicateurs métier séparés proposés :
- Catégories Products non traduites et nombre de produits concernés.
- Produits sans catégorie, comptés séparément.
- Traductions inutilisées.
- Libellés anglais partagés entre plusieurs catégories portugaises.
- Variantes d'écriture, espaces et caractères inhabituels.

Ces indicateurs ne doivent pas augmenter quality_issue_count. Aucune règle unique(product_category_name_english), traduction automatique, normalisation persistée, suppression ou dédoublonnage n'est autorisé à cette étape.

## Vérifications et suite

Commandes PowerShell réellement exécutées :

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

Suite existante : **540 passed in 27.10s**. pip check : **No broken requirements found**. Code complet du notebook exécuté avec Python, assertion de cardinalité et empreintes des deux sources réussies. JSON du notebook relu, cellules compilées, sorties vides vérifiées.

**55 empreintes SHA256 protégées inchangées**, incluant les CSV sources, sorties existantes, code/tests et anciens notebooks.

Créés : notebooks/08_category_translation_exploration.ipynb et ce rapport. Modifié parmi les fichiers existants : docs/PROGRESS.md uniquement. Aucun autre validateur ou sortie modifié ; aucun commit/push.

Prochaine action : attendre l'accord sur les résultats et ce contrat avant développement du neuvième validateur. Phase 1 reste en cours.
