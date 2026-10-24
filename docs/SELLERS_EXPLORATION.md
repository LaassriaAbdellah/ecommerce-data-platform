# Exploration de Sellers — 2026-10-24

## Périmètre et reproduction

Phase 1, exploration uniquement : aucun sellers_validator.py, aucune sortie Sellers dans data/processed/, aucun statut valid/review attribué. Le notebook [05_sellers_exploration.ipynb](../notebooks/05_sellers_exploration.ipynb) reprend les conventions Path/Pandas, contrôles d'empreintes et jointures contrôlées des explorations précédentes.

Exécuter les cellules de haut en bas, depuis la racine ou notebooks/, avec le noyau .venv du projet sur C:. Le code enregistré a été exécuté avec Python ; le notebook est fourni sans sorties enregistrées, sans lancement d'un noyau Jupyter.

- Python 3.11.0, Pandas 3.1.0, environnement du projet sur C:.
- Espace initial C: 4,536 Gio ; aucune installation ni téléchargement.
- Sellers : 174703 octets ; DataFrame string : 0.818 Mio (mémoire profonde du seul DataFrame, pas le pic du processus).
- Order Items : lecture de seller_id uniquement ; Customers : lecture des trois colonnes géographiques uniquement. Pas de lecture de Geolocation, pas de service lourd.
- Sources inchangées, lecture seule ; aucune normalisation écrite dans les CSV.

| Source | SHA256 |
|---|---|
| sellers | 1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e |
| items | 0bc4d068c4fe38cbb01bd90e8746e3c613fe7b4baef75fab7b0e329701c3e279 |
| customers | 983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2 |

## Schéma, grain et complétude

**3 095 lignes, quatre colonnes, 3 095 seller_id distincts.** Grain : une ligne par vendeur. Aucun doublon complet excédentaire, aucune ligne impliquée dans un doublon d'identifiant.

| Colonne | Type inféré | Type retenu pour l'analyse | Nuls | Chaînes vides | Espaces seuls |
|---|---|---|---|---|---|
| seller_id | str | string | 0 | 0 | 0 |
| seller_zip_code_prefix | int64 | string | 0 | 0 | 0 |
| seller_city | str | string | 0 | 0 | 0 |
| seller_state | str | string | 0 | 0 | 0 |

Aucun espace en bordure des quatre colonnes. Les chaînes vides sont vérifiées avec keep_default_na=False pour distinguer leur représentation brute des nulls Pandas. Les seller_id sont tous renseignés et au format hexadécimal minuscule de 32 caractères ; ce dernier constat ne devient pas une contrainte supplémentaire sans validation.

## Préfixes postaux

- Tous les préfixes ont exactement **cinq chiffres ASCII** ; aucune valeur 00000.
- **2 246 préfixes distincts**, minimum lexical 01001, maximum 99730. Ce sont des codes, pas des mesures : ces bornes ne servent pas de seuils de validation.
- **1 027 vendeurs ont un préfixe commençant par zéro**, soit 33.18 %.
- Exemples préservés : 04195, 01529, 01222, 05372, 05138, 04156, 09850, 04857, 02261, 03562.
- La lecture inférée donne int64 et perd les zéros initiaux ; dtype="string" les conserve, comme dans Customers.
- Le format valide ne garantit ni l'attribution officielle ni la cohérence géographique du code.
- Préfixes les plus fréquents :

| Préfixe | Vendeurs |
|---|---|
| 13481 | 7 |
| 13660 | 10 |
| 13920 | 9 |
| 14020 | 8 |
| 14940 | 49 |
| 16200 | 9 |
| 35530 | 6 |
| 37540 | 7 |
| 87050 | 8 |
| 01026 | 8 |

## États et villes

**23 codes d'État présents**, tous dans la liste des 27 codes utilisée par Customers. AL, AP, RR et TO ne sont pas représentés : absence de vendeurs dans l'échantillon, pas anomalie.

| État | Vendeurs |
|---|---|
| SP | 1849 |
| PR | 349 |
| MG | 244 |
| SC | 190 |
| RJ | 171 |
| RS | 129 |
| GO | 40 |
| DF | 30 |
| ES | 23 |
| BA | 19 |
| CE | 13 |
| PE | 9 |
| PB | 6 |
| RN | 5 |
| MS | 5 |
| MT | 4 |
| RO | 2 |
| SE | 2 |
| AC | 1 |
| PI | 1 |
| MA | 1 |
| AM | 1 |
| PA | 1 |

**611 libellés de ville distincts**, tous non vides et en minuscules. Une ligne contient un accent décomposé Unicode ; 33 contiennent une ponctuation selon le motif [^\\w\\s].

| Ville (top 20) | Vendeurs |
|---|---|
| sao paulo | 694 |
| curitiba | 127 |
| rio de janeiro | 96 |
| belo horizonte | 68 |
| ribeirao preto | 52 |
| guarulhos | 50 |
| ibitinga | 49 |
| santo andre | 45 |
| campinas | 41 |
| maringa | 40 |
| sao jose do rio preto | 33 |
| sao bernardo do campo | 32 |
| osasco | 32 |
| sorocaba | 32 |
| brasilia | 28 |
| porto alegre | 28 |
| londrina | 26 |
| goiania | 23 |
| joinville | 22 |
| blumenau | 21 |

### Variations d'écriture

Méthode exploratoire : casefold → décomposition NFKD et retrait des marques d'accent → ponctuation remplacée par des espaces → espaces multiples réduits. Comparaison à État identique. Aucune valeur source remplacée.

Six groupes comportent plusieurs libellés pour une même clé exploratoire ; **723 lignes appartiennent à ces groupes**. Ce nombre inclut les libellés fréquents de référence et ne signifie pas 723 erreurs.

| État | Clé exploratoire | Libellés et effectifs |
|---|---|---|
| PR | sao jose dos pinhais | "sao jose dos pinhais": 9 ; "sao  jose dos pinhais": 1 |
| RJ | rio de janeiro rio de janeiro | "rio de janeiro \\rio de janeiro": 1 ; "rio de janeiro / rio de janeiro": 1 |
| SP | ferraz de vasconcelos | "ferraz de vasconcelos": 3 ; "ferraz de  vasconcelos": 1 |
| SP | santa barbara d oeste | "santa barbara d'oeste": 4 ; "santa barbara d´oeste": 2 ; "santa barbara d oeste": 1 |
| SP | sao paulo | "sao paulo": 694 ; "são paulo": 1 ; "sao  paulo": 1 |
| SP | sao paulo sp | "sao paulo - sp": 3 ; "sao paulo sp": 1 |

Cette méthode repère espaces, accents et ponctuation, mais ne résout pas les fautes ni les suffixes d'État : sao paulo et sao paulo - sp restent deux clés distinctes. Exemples supplémentaires à examiner : sao pauo, cascavael, floranopolis, mogi das cruses ; suffixes comme lages - sc ; libellé numérique 04482255. Ces libellés sont observés, aucune ville correcte n'est déduite automatiquement.

## Cohérence géographique : signaux, pas erreurs confirmées

### Comparaisons internes Sellers

- **23 libellés exacts de ville apparaissent dans plusieurs États**. Des homonymes peuvent être légitimes.
- **17 préfixes sont associés à plusieurs États**, concernant 45 vendeurs.
- **34 préfixes sont associés à plusieurs libellés exacts de ville**. Variantes, quartiers ou couverture postale peuvent expliquer certains cas.
- Exemple : 85960 est associé à marechal candido rondon avec PR, SP et PA ; 95076 à caxias do sul avec RS et SP ; 21210 à rio de janeiro avec RJ et RN.
- Ces constats ne désignent pas automatiquement la ligne erronée et ne permettent pas une correction majoritaire.

### Comparaison avec Customers

Pour chaque préfixe Seller, constituer les ensembles d'États et de clés de villes observés dans Customers. Utiliser l'appartenance à ces ensembles, sans jointure multipliant les lignes. Customers n'est pas un référentiel officiel et peut contenir des erreurs ou être incomplet.

| Indicateur | Vendeurs concernés |
|---|---|
| Préfixe présent dans Customers | 3004 |
| Préfixe absent de Customers | 91 |
| État non observé pour un préfixe présent | 35 |
| Clé de ville non observée pour un préfixe présent | 89 |

Les 91 préfixes non observés ne sont pas inclus dans les deux indicateurs de divergence. Les groupes peuvent se chevaucher : ne pas additionner ces nombres comme un total d'anomalies.

Exemples de divergences d'État (valeur Seller conservée, aucune correction) :

| seller_id | Préfixe | Ville | État Seller |
|---|---|---|---|
| f410c8873029fcc3809b9df6d0b28914 | 95076 | caxias do sul | SP |
| 392f7f2c797e4dc077e4311bde2ab8ce | 21210 | rio de janeiro | RN |
| 1284de4ae8aa26997e748c851557cf0e | 85301 | laranjeiras do sul | SP |
| 8b181ee5518df84f18f4e1a43fe07923 | 87360 | goioere | SP |
| 3d700782d7818f2c1e0d7a9e9d75fc00 | 86170 | sertanopolis | SP |
| f626e15b7314c267e4429010866f70e9 | 85960 | marechal candido rondon | SP |
| c716e0b86ed568878475b60fbb6323ad | 22783 | rio de janeiro | SP |
| c8771b1a10bb99bb34d3c459c5cffb53 | 36512 | tocantins | SP |
| 48436dade18ac8b2bce089ec2a041202 | 27277 | volta redonda | SP |
| 289cdb325fb7e7f891c38608bf9e0962 | 31570 | belo horizonte | SP |

Les listes complètes des divergences d'État et préfixes multi-États, ainsi que 20 exemples d'écarts de ville, sont calculées dans le notebook. Aucun appel externe, géocodage ou exploration de Geolocation réalisé.

## Relation avec Order Items

| Mesure | Résultat |
|---|---|
| item_rows | 112650 |
| distinct_item_sellers | 3095 |
| missing_item_seller_ids | 0 |
| unknown_seller_item_rows | 0 |
| unknown_distinct_sellers | 0 |
| unused_seller_rows | 0 |
| joined_rows | 112650 |

Les 112 650 lignes Item référencent exactement les 3 095 vendeurs. Aucun seller_id Item manquant, aucune référence inconnue, aucun vendeur sans article. Jointure gauche avec validate="many_to_one" : toujours 112 650 lignes.

Le nombre de lignes Item par vendeur varie de 1 à 2 033 ; médiane 8, Q1=2, Q3=24, moyenne 36,3974. Ce sont des **lignes Item**, pas des commandes distinctes ni des unités vendues déduites d'une quantité absente. Plusieurs articles par vendeur sont normaux.

## Règles proposées — à valider avant implémentation

| Règle structurelle proposée | Motif |
|---|---|
| Quatre colonnes obligatoires | Schéma attendu |
| seller_id renseigné, non vide et unique | Clé du grain vendeur |
| seller_zip_code_prefix renseigné et composé de cinq chiffres ASCII | Préserver les zéros, sans seuil numérique ni validation géographique implicite |
| seller_city renseignée et non vide | Ne pas interdire accents, ponctuation ou variantes par défaut |
| seller_state renseigné et dans les 27 codes existants | Réutiliser la convention Customers, sans restreindre aux 23 observés |
| Référence seller_id Item existante dans Sellers | Contrôle inter-tables côté Item, à traiter séparément sans modifier le validateur actuel |

Indicateurs séparés proposés : vendeurs sans article, préfixes inconnus de Customers, villes à variantes, villes multi-États, préfixes multivilles/multi-États, divergences de ville/État avec Customers et libellés inhabituels. Ils ne doivent pas alimenter quality_issue_count sans politique métier validée.

Aucun rejet pour zéro initial, rareté d'un État, accents, ponctuation, forte activité ou homonyme. Pas de nettoyage automatique, remplissage, dédoublonnage ou dictionnaire de correction inventé.

## Vérifications réalisées et suite

- Code enregistré du notebook exécuté avec Python : calcul et assertions d'intégrité réussis. Pas d'exécution avec un noyau Jupyter.
- Une première impression console sous Windows cp1252 a échoué sur l'accent Unicode décomposé ; calcul réexécuté avec capture Unicode en mémoire et affichage JSON échappé. Il s'agit d'une limite d'affichage, pas d'une corruption des sources.
- Suite existante : **298 passed in 21.57s**.
- pip check : **No broken requirements found**.
- Commandes PowerShell depuis la racine :

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
```

Fichiers de cette tâche : création du notebook et de ce rapport ; mise à jour de docs/PROGRESS.md. Aucun validateur, helper, test existant, donnée source ou ancienne sortie modifié. Aucun commit/push.

Prochaine action : faire valider les résultats, les règles structurelles et la séparation des indicateurs géographiques avant de développer Sellers. Phase 1 toujours en cours.
