# Exploration de Geolocation — 2026-10-24

## Périmètre, ressources et reproduction

Phase 1, exploration uniquement. Aucun geolocation_validator.py, CSV de sortie Geolocation ou statut valid/review créé.

Notebook : [07_geolocation_exploration.ipynb](../notebooks/07_geolocation_exploration.ipynb). Exécuter de haut en bas depuis la racine ou notebooks/, avec le .venv du projet sur C:. Conventions Path/Pandas, contrôles SHA256 et séparation structure/métier reprises des explorations précédentes.

- Python 3.11.0, Pandas 3.1.0, espace libre initial C: 3,917 Gio ; aucune installation.
- Source : **61 273 883 octets**, soit 58.435 Mio.
- Un seul tableau principal : villes/États en category, préfixes et coordonnées sources en string pour préserver les zéros initiaux et mesurer les doublons exacts sans arrondi.
- Mémoire profonde du seul tableau : **206,615 Mio**. Les séries numériques, groupements et tables de correspondance s'y ajoutent ; ce nombre ne représente pas le pic mémoire du processus.
- Les empreintes sont calculées par blocs de 1 Mio, sans charger chaque fichier complet en mémoire. Les lectures Sellers/Customers ne portent que sur les trois colonnes géographiques. Aucun service lourd.
- Code complet enregistré exécuté avec Python, pas via noyau Jupyter. Notebook livré sans sorties sauvegardées.

| Source | SHA256 |
|---|---|
| geolocation | b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6 |
| sellers | 1f643d2b950373b85735e7794b20986f528d7a000432e7c6f9bcbb44d0846a0e |
| customers | 983a422239e1712ded753b3bf9ecf47dc73f144d306029dcfa99e70a226883d2 |

Aucune source réécrite, aucune déduplication ou correction persistée.

## Dimensions, types et complétude

**1 000 163 lignes et cinq colonnes.** Grain : enregistrement géographique, sans identifiant de ligne fourni. Ni le préfixe ni la ligne complète ne sont uniques.

| Colonne | Type inféré sur les 1 000 premières lignes | Type utilisé dans le tableau complet | Champs vides | Espaces seuls |
|---|---|---|---|---|
| geolocation_zip_code_prefix | int64 | string | 0 | 0 |
| geolocation_lat | float64 | string | 0 | 0 |
| geolocation_lng | float64 | string | 0 | 0 |
| geolocation_city | str | category | 0 | 0 |
| geolocation_state | str | category | 0 | 0 |

L'inférence sur 1 000 lignes est un échantillon, pas une preuve sur le fichier complet. En revanche les contrôles de format et conversion numérique couvrent **toutes les lignes**. Les colonnes numériques converties sont toutes deux de type nullable Float64.

keep_default_na=False conserve la représentation source : aucun null du parseur, champ vide ou espace seul détecté. Un seul libellé de ville a un espace en bordure ; aucune correction appliquée.

## Doublons complets et préfixes

- **261 831 occurrences excédentaires** après la première ligne identique.
- **390 005 lignes impliquées** dans des groupes de doublons complets, premières occurrences incluses.
- **738 332 lignes complètes distinctes**.
- Comparaison sur les cinq champs sources, coordonnées textuelles comprises ; pas de tolérance numérique ni arrondi.
- Ces doublons sont proposés comme indicateurs : conserver le brut et définir une politique avant de supprimer une ligne.

Préfixes :
- **19 015 valeurs distinctes**, toutes de cinq chiffres ASCII ; aucun 00000.
- **245 733 lignes** ont un zéro initial, représentant **4 354 préfixes distincts**.
- Minimum lexical 01001, maximum 99990 ; ces bornes observées ne sont pas des règles de rejet.
- **17 972 préfixes ont plusieurs lignes** ; lignes par préfixe : médiane 29, P95=180, P99=353, maximum 1 146.
- **17 781 préfixes ont plusieurs paires numériques de coordonnées distinctes**.
- **720 154 triplets distincts (préfixe, latitude, longitude)** mondialement valides.
- **8 556 préfixes ont plusieurs libellés bruts de ville**, et **huit plusieurs États**. Les variantes orthographiques participent au premier nombre.
- Ne pas imposer unique(geolocation_zip_code_prefix).

## Validité et distribution des coordonnées

Bornes géographiques possibles, inclusives : latitude [-90,90], longitude [-180,180]. Ces bornes mondiales ne valident ni le pays, ni le lien avec la ville/État/préfixe.

Pour chaque axe : **zéro manque, valeur non convertible, valeur infinie ou valeur finie hors bornes**. Zéro paire de coordonnées structurellement invalide ; aucune coordonnée égale à zéro.

| Mesure | Latitude | Longitude |
|---|---|---|
| min | -36.605374 | -101.466766 |
| 1% | -30.104536 | -57.650700 |
| 25% | -23.603546 | -48.573172 |
| 50% | -22.919377 | -46.637879 |
| 75% | -19.979620 | -43.767709 |
| 99% | -2.501042 | -34.938641 |
| max | 45.065933 | 121.105394 |
| mean | -21.176153 | -46.390541 |
| std | 5.715866 | 4.269748 |

Ces distributions portent sur toutes les lignes, doublons inclus ; elles ne représentent ni une distribution de clients ni une surface géographique uniforme.

**1 336 latitudes positives** et **trois longitudes positives**. Un signe positif n'est pas en soi une erreur ; aucun polygone officiel du Brésil ni référentiel géographique externe n'a été utilisé.

Exemples de points extrêmes observés, à examiner sans correction :

| Préfixe | Ville | État | Latitude | Longitude |
|---|---|---|---|---|
| 98780 | santa rosa | RS | -36.6053744107061 | -64.28394645581311 |
| 57319 | pau d'arco | AL | 45.06593318269697 | 9.341527629906514 |
| 29654 | santo antonio do canaa | ES | 21.65754744931478 | -101.46676644931476 |
| 95130 | santa lucia do piai | RS | 14.585072541779617 | 121.10539381057764 |

## Villes et États

**8 011 libellés bruts de ville** et **5 930 clés de ville normalisées**. La normalisation exploratoire est casefold → NFKD → retrait des accents → ponctuation en espaces → espaces multiples réduits ; les données originales restent inchangées.

**2 128 groupes de variantes à État identique**. Les clés communes ne prouvent pas l'identité officielle des localités ; la méthode ne résout pas les fautes, quartiers, homonymes ou frontières administratives.

Exemples : acrelandia/acrelândia ; brasileia/brasiléia ; barra de santo antonio/barra de santo antônio/barra de  santo antônio. Il s'agit de variations observées, sans choix arbitraire d'une écriture correcte.

Les **27 codes d'État et du District fédéral** de la convention Customers sont présents ; aucun code inconnu ou vide.

| Code | Lignes |
|---|---|
| SP | 404268 |
| MG | 126336 |
| RJ | 121169 |
| RS | 61851 |
| PR | 57859 |
| SC | 38328 |
| BA | 36045 |
| GO | 20139 |
| ES | 16748 |
| PE | 16432 |
| DF | 12986 |
| MT | 12031 |
| CE | 11674 |
| PA | 10853 |
| MS | 10431 |
| MA | 7853 |
| PB | 5538 |
| RN | 5041 |
| PI | 4549 |
| AL | 4183 |
| TO | 3576 |
| SE | 3563 |
| RO | 3478 |
| AM | 2432 |
| AC | 1301 |
| AP | 853 |
| RR | 646 |

Préfixes multi-États : 02116 (SP/RN), 04011 (SP/AC), 21550 (RJ/AC), 23056 (RJ/AC), 72915 (GO/DF), 78557 (MT/RO), 79750 (MS/RS), 80630 (PR/SC). Les associations sont observées dans le fichier ; aucune n'est considérée comme référence officielle ou corrigée par majorité.

## Dispersion des points d'un préfixe

Méthode : étendue max-min séparément pour latitude et longitude, par préfixe, uniquement sur les paires finies dans les bornes mondiales. Tous les préfixes sont comparables ici. Unité **degré** ; ce n'est ni une distance en kilomètres ni le diamètre réel du nuage.

| Statistique | Étendue latitude (°) | Étendue longitude (°) |
|---|---|---|
| 50% | 0.014758 | 0.015757 |
| 95% | 0.167710 | 0.197328 |
| 99% | 1.497404 | 1.846026 |
| max | 77.025708 | 72.552315 |

Les dix plus grandes étendues de latitude, sans seuil de rejet :

| Préfixe | Étendue latitude (°) | Étendue longitude (°) |
|---|---|---|
| 28155 | 77.025708 | 72.552315 |
| 45936 | 72.946338 | 52.126852 |
| 28165 | 71.752907 | 45.383863 |
| 57319 | 68.324157 | 56.648958 |
| 28595 | 66.345736 | 36.172933 |
| 83810 | 64.927069 | 41.036893 |
| 28333 | 59.483599 | 35.787612 |
| 68379 | 59.328130 | 32.070324 |
| 35179 | 56.043348 | 55.578362 |
| 46560 | 51.981085 | 37.272232 |

Les étendues atteignant plusieurs dizaines de degrés sont des signaux forts d'hétérogénéité des coordonnées pour un même code. Elles justifient une investigation métier, mais ne prouvent pas quelle ligne est correcte. Aucune moyenne/médiane ou premier point n'a été choisi pour remplacer le groupe.

## Relations avec Sellers et Customers

La couverture compare l'appartenance aux ensembles de préfixes. Pour les préfixes connus, ville normalisée et État sont comparés aux ensembles de valeurs observées. Aucune jointure brute ne multiplie les lignes.

| Mesure | Sellers | Customers |
|---|---|---|
| Lignes source | 3095 | 99441 |
| Préfixes source distincts | 2246 | 14994 |
| Lignes couvertes | 3088 | 99163 |
| Couverture en lignes (%) | 99.7738 | 99.7204 |
| Lignes avec préfixe absent | 7 | 278 |
| Préfixes distincts absents | 7 | 157 |
| État non observé sur préfixe connu | 35 | 0 |
| Ville normalisée non observée sur préfixe connu | 89 | 24 |
| Lignes sur préfixe à plusieurs coordonnées valides | 3078 | 98890 |
| Lignes sur préfixe contenant une coordonnée mondialement invalide | 0 | 0 |
| Lignes couvertes sans coordonnée mondialement valide | 0 | 0 |

Préfixes Sellers absents : 82040, 91901, 72580, 02285, 07412, 71551, 37708.
Exemples Customers absents (20 des 157) : 72300, 11547, 64605, 72465, 07729, 72904, 35408, 78554, 73369, 08980, 29949, 65137, 28655, 73255, 28388, 06930, 71676, 64047, 61906, 83210.

Les écarts ville/État sont calculés uniquement sur les préfixes présents ; les absences constituent une catégorie séparée. Les groupes peuvent se chevaucher ; leurs nombres ne s'additionnent pas en un total d'erreurs.

Sellers et Customers n'ont pas de coordonnées individuelles : aucune incohérence point-à-point ne peut être calculée. Plusieurs points pour leur préfixe signalent une ambiguïté, pas une localisation individuelle certaine. Les fortes dispersions décrites plus haut restent pertinentes même si la couverture du code est complète.

**Geolocation n'est ni un référentiel officiel ni exhaustif.** Une absence ou divergence ne prouve pas une erreur dans Sellers/Customers ; elle peut provenir de Geolocation ou d'une différence de représentation.

## Contrat de validation proposé — en attente d'accord

| Règle structurelle proposée | Politique |
|---|---|
| Cinq colonnes obligatoires | Noms Olist conservés |
| Préfixe renseigné de cinq chiffres ASCII | String, sans padding ni conversion entière |
| Latitude et longitude renseignées, numériques, finies | Distinguer absence, non-convertibilité et infini |
| Latitude dans [-90,90], longitude dans [-180,180] | Bornes inclusives uniquement ; pas de seuil régional arbitraire |
| Ville et État renseignés/non vides | Ne pas rejeter les accents ou variations par défaut |
| État dans les 27 codes existants | Réutiliser la convention Customers |

Indicateurs séparés : doublons complets, plusieurs lignes/coordonnées par préfixe, variantes de villes, préfixes multivilles/multi-États, dispersion et points extrêmes, couverture et divergences avec Sellers/Customers.

Aucune règle unique(prefix), aucun rejet par doublon complet, signe de coordonnée, distance, enveloppe arbitraire du Brésil ou seuil de dispersion. La stratégie de dédoublonnage et de coordonnée représentative nécessite une décision ultérieure explicite.

## Vérifications et prochaine action

Commandes PowerShell réellement exécutées :

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
```

Suite existante : **461 passed in 25.17s** ; pip check : **No broken requirements found**. Code complet enregistré du notebook exécuté avec Python ; contrôle SHA256 des trois sources réussi. Aucune exécution Jupyter revendiquée.

Fichiers créés : notebooks/07_geolocation_exploration.ipynb et ce rapport. Modifié parmi les fichiers existants : docs/PROGRESS.md uniquement. Les changements Git antérieurs sont préservés.

Prochaine action : validation des résultats, du grain et du contrat avant développement du validateur Geolocation. Phase 1 toujours en cours ; aucun commit/push.
