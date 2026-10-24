# Exploration de Reviews — 2026-10-24

## Périmètre et reproduction

Phase 1, exploration uniquement. Aucun reviews_validator.py, statut valid/review ou fichier de sortie Reviews créé.

Notebook : [06_reviews_exploration.ipynb](../notebooks/06_reviews_exploration.ipynb), à exécuter de haut en bas depuis la racine ou notebooks/, avec le .venv du projet sur C:. Conventions Path/Pandas, lecture seule, empreintes SHA256, jointure many_to_one et séparation des anomalies/indicateurs reprises des explorations précédentes.

Code enregistré exécuté avec Python, sans lancement de noyau Jupyter ; notebook livré sans sorties sauvegardées. Python 3.11.0, Pandas 3.1.0. Espace initial C: 3,968 Gio ; aucune installation. Reviews : 14451670 octets ; mémoire profonde du seul DataFrame 42.747 Mio, pas le pic total. Orders limité à quatre colonnes. Aucun service lourd.

| Source | SHA256 |
|---|---|
| reviews | 012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7 |
| orders | 8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf |

Les empreintes sont contrôlées avant/après calcul. Aucun texte de commentaire intégral n'est reproduit dans ce rapport.

## Dimensions, types et valeurs absentes

**99 224 lignes, sept colonnes.** Les types sont inférés par Pandas ; les dates restent des chaînes tant qu'elles ne sont pas converties explicitement.

| Colonne | Type inféré | Nuls Pandas | Champs source vides | Espaces seuls non vides |
|---|---|---|---|---|
| review_id | str | 0 | 0 | 0 |
| order_id | str | 0 | 0 | 0 |
| review_score | int64 | 0 | 0 | 0 |
| review_comment_title | str | 87656 | 87656 | 2 |
| review_comment_message | str | 58247 | 58247 | 27 |
| review_creation_date | str | 0 | 0 | 0 |
| review_answer_timestamp | str | 0 | 0 | 0 |

Les champs vides correspondent aux nulls Pandas, pas à des observations supplémentaires. Les chaînes composées uniquement d'espaces ajoutent deux titres et 27 messages à l'absence fonctionnelle. Espaces en bordure : 1 998 titres, 9 451 messages, zéro dans les autres colonnes ; aucune correction appliquée.

**Aucun doublon complet**, ni excédentaire ni impliqué. Aucun identifiant absent/vide ; les deux identifiants suivent tous le format hexadécimal minuscule de 32 caractères, constat descriptif sans nouvelle contrainte imposée.

## Identifiants, grain et clés candidates

| Mesure | review_id | order_id |
|---|---|---|
| Valeurs distinctes | 98410 | 98673 |
| Valeurs répétées | 789 | 547 |
| Lignes impliquées dans ces répétitions | 1603 | 1098 |
| Occurrences excédentaires après la première | 814 | 551 |
| Nombre maximal de lignes par valeur | 3 | 3 |

- review_id : 97 621 apparaissent une fois, 764 deux fois et 25 trois fois.
- order_id : 98 126 apparaissent une fois, 543 deux fois et quatre trois fois.
- Les **789 review_id répétés concernent tous plusieurs commandes distinctes**. Leurs cinq autres champs (note, titre, message et deux dates) sont identiques au sein de chaque ID, y compris les valeurs absentes. Aucun de ces groupes n'a un contenu différent.
- Les **99 224 paires (review_id, order_id) sont distinctes** : aucun doublon de paire.
- Les 547 commandes avec plusieurs lignes possèdent plusieurs review_id distincts ; **202 commandes ont plusieurs notes différentes**.

Le grain observé est une association entre un avis et une commande. Un avis réutilisé sur plusieurs commandes et plusieurs avis pour une commande sont présents ; le CSV seul n'établit pas leur cause (questionnaire partagé, historique ou autre). Ne pas présenter une explication hypothétique comme démontrée.

La paire est une **clé candidate observée**, pas une garantie contractuelle de la source. Une règle unique(review_id) rejetterait 1 603 lignes ; unique(order_id) en rejetterait 1 098, sans justification suffisante. Ne pas dédupliquer sur l'un de ces identifiants seul.

Une moyenne de notes sur les lignes, une moyenne par review_id distinct ou une note choisie par commande n'ont pas le même grain. Ne pas choisir arbitrairement le premier/dernier avis ni rejoindre directement Reviews × Items × Payments pour des agrégats.

## Notes

| Note | Lignes |
|---|---|
| 1 | 11424 |
| 2 | 3151 |
| 3 | 8179 |
| 4 | 19142 |
| 5 | 57328 |

Moyenne descriptive **4,0864 sur les 99 224 lignes**. Aucun score absent, non numérique, non fini, fractionnaire ou hors de [1,5]. Cette moyenne ne constitue pas un KPI dédupliqué par commande ou par avis distinct.

## Complétude des commentaires

Absence fonctionnelle = champ vide/null ou composé uniquement d'espaces, sans modifier les valeurs sources.

| Champ | Absent fonctionnellement | Présent | Médiane de longueur renseignée | Maximum |
|---|---|---|---|---|
| Titre | 87658 | 11566 | 10 | 26 |
| Message | 58274 | 40950 | 53 | 208 |

| Combinaison | Lignes |
|---|---|
| Titre et message absents | 56537 |
| Titre et message présents | 9829 |
| Titre seul | 1737 |
| Message seul | 31121 |
| Au moins un commentaire absent (union) | 89395 |

Les quatre premiers groupes sont disjoints et totalisent 99 224. Le dernier est une union et ne s'ajoute pas aux autres. Les commentaires sont proposés comme facultatifs : leur absence n'invalide ni la note ni l'avis. Les statistiques de longueur utilisent le texte original renseigné, sans suppression d'espaces.

## Dates et délais

Format observé : %Y-%m-%d %H:%M:%S. Les deux colonnes sont présentes et intégralement convertibles au format explicite ; aucune date nécessitant seulement format="mixed", aucun écart au motif source.

| Colonne | Minimum | Maximum | Lignes à minuit |
|---|---|---|---|
| review_creation_date | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 | 99139 |
| review_answer_timestamp | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 | 1 |

99 139 créations sont à minuit, donc 85 ne le sont pas. La comparaison avec un horodatage précis doit tenir compte de cette précision. Aucun fuseau fourni ; calculs naïfs sans conversion de fuseau inventée.

Délai = (review_answer_timestamp - review_creation_date) en jours de 24 heures, sur 99 224 paires valides :

| Statistique | Jours |
|---|---|
| count | 99224.0000 |
| mean | 3.1490 |
| std | 9.8900 |
| min | 0.0892 |
| 25% | 1.0049 |
| 50% | 1.6749 |
| 75% | 3.1036 |
| 95% | 6.9722 |
| 99% | 22.0708 |
| max | 518.6992 |

- Aucun délai négatif ou nul.
- 4 914 lignes au-delà de sept jours ; 682 au-delà de 30 jours. Ces repères sont descriptifs, pas des seuils de rejet ni des SLA prouvés.
- Maximum 518,6992 jours : cas inhabituel à analyser, sans suppression automatique.
- Le nom answer ne prouve pas une réponse du vendeur à un commentaire : le rôle exact de ces événements doit être confirmé avant de définir un KPI métier de temps de réponse.

## Relations avec Orders

Toutes les 99 224 lignes Reviews référencent une commande existante. Jointure gauche many_to_one vers Orders : **99 224 lignes conservées**, sans multiplication.

- Orders : 99 441 commandes.
- 98 673 commandes ont au moins une ligne Reviews.
- **768 commandes sans avis**, dont 646 delivered.
- **547 commandes avec plusieurs avis**, soit 1 098 lignes ; quatre ont trois avis.

| Statut de commande | Commandes sans avis |
|---|---|
| delivered | 646 |
| shipped | 75 |
| canceled | 20 |
| unavailable | 14 |
| processing | 6 |
| invoiced | 5 |
| created | 2 |

Distribution des lignes Reviews selon le statut actuel de la commande :

| Statut | Lignes Reviews |
|---|---|
| delivered | 96361 |
| shipped | 1043 |
| canceled | 609 |
| unavailable | 597 |
| invoiced | 313 |
| processing | 296 |
| created | 3 |
| approved | 2 |

Les avis sur commandes non livrées ne sont pas automatiquement invalides. Statut actuel et événement historique ne sont pas interchangeables.

### Chronologie inter-tables

| Indicateur | Lignes Reviews |
|---|---|
| creation_before_purchase_rows | 74 |
| answer_before_purchase_rows | 63 |
| rows_with_delivery_for_comparison | 96359 |
| creation_before_delivery_rows | 8320 |
| creation_before_delivery_calendar_day_rows | 5127 |
| answer_before_delivery_rows | 4795 |
| creation_without_recorded_delivery_rows | 2865 |

Les 8 320 créations avant l'horodatage de livraison deviennent 5 127 avant le jour de livraison : 3 193 sont le même jour mais avant l'heure enregistrée. Ne pas transformer cet effet de précision en erreur certaine.

Les 74 créations et 63 réponses avant achat sont des incohérences potentielles à examiner, sans correction automatique. Ces groupes peuvent se chevaucher. Pour les 2 865 créations sans date de livraison enregistrée, aucune comparaison à la livraison n'est possible.

## Contrat de validation proposé — en attente d'accord

| Contrôle structurel proposé | Politique |
|---|---|
| Sept colonnes obligatoires | Respecter les noms Olist |
| review_id et order_id renseignés/non vides | Réutiliser les helpers existants |
| Paire (review_id, order_id) unique | Candidate conforme au fichier ; politique à confirmer |
| review_score numérique, fini, entier de 1 à 5 | Booléens à refuser dans le futur validateur |
| Dates renseignées et convertibles | Absence distincte de non-convertibilité ; conversion sur copie |
| Référence order_id existante dans Orders | Contrôle d'intégrité référentielle |
| Commentaires facultatifs | Vide/null/espaces signalés séparément, texte source conservé |

Indicateurs métier distincts de quality_issue_count : commentaires absents, review_id partagé, avis multiples par commande, notes contradictoires par commande, commandes sans avis par statut, délais et chronologie avant achat/livraison, précision à minuit et dates de livraison absentes. Aucun seuil temporel arbitraire ne devient une erreur structurelle.

Conserver toutes les lignes jusqu'à validation d'une politique de grain, sélection et éventuel dédoublonnage. Ne pas forcer unique(review_id) ou unique(order_id).

## Vérifications et suite

Commandes PowerShell réellement exécutées :

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pip check
```

Résultats : **381 passed in 17.95s** ; **No broken requirements found**. Code complet enregistré du notebook exécuté avec Python et assertions de cardinalité/empreintes réussies ; pas de lancement Jupyter.

Créés : notebooks/06_reviews_exploration.ipynb et ce rapport. Modifié parmi les fichiers existants : docs/PROGRESS.md uniquement. Aucune donnée source, sortie dérivée, ancien notebook, validateur, helper ou test modifié ; aucun commit/push.

Prochaine action : validation des résultats, du grain et du contrat avant développement du validateur Reviews. Phase 1 reste en cours.
