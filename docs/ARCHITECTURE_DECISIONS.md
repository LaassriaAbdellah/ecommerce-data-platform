# Décisions techniques

## 2026-10-23 — Mutualisation des validations et grain Customers

- Séparer les helpers structurels (common.py), l'agrégation des résultats (quality_engine.py) et les règles métier de chaque table. Orders et Customers réutilisent les composants existants.
- Le moteur exige des masques Series booléens avec index identique au DataFrame. Les valeurs nulles d'un masque sont traitées comme False ; prévoir des règles de valeurs manquantes explicites.
- Le rapport générique compte des lignes (total_rows, valid_rows, review_rows) avec entity et anomalies_by_rule. Orders conserve ses clés historiques via adaptation ; Customers utilise le format générique.
- check_duplicate_ids() marque toutes les occurrences (keep=False). Les validateurs excluent les identifiants absents de la règle de doublon ; pas de dédoublonnage ou suppression automatique.
- Customers a pour clé attendue customer_id. customer_unique_id peut se répéter légitimement ; 96 096 identifiants distincts et 2 997 récurrents observés sur 99 441 lignes.
- Préfixe postal conservé comme texte à la lecture (dtype string), jamais converti en nombre ni complété arbitrairement par des zéros. La règle vérifie cinq chiffres ; les États sont contrôlés dans une liste de 27 codes.
- Sept règles Customers présentes : identifiants requis/uniques, ville et État non vides, format postal et État autorisé. Zéro anomalie signifie seulement satisfaction de ces règles, pas exactitude géographique garantie.
- Les quatre sorties Orders/Customers sont dérivées et régénérables ; audit via fonctions en mémoire sans réécrire les sorties existantes.
- 21 tests réussis à l'audit ; couverture encore partielle. Requirements de phase 1 à compléter séparément ; pas d'installation pendant cette intervention.
- Prochaine demande : exploration order_items seulement après accord, sans démarrer une phase suivante ni changer la roadmap. Documenter le grain composite et éviter le double comptage avec payments.
- Les décisions antérieures sur le brut, la traçabilité, la séparation Jupyter/Python et l'usage exclusif de C: restent applicables.

## 2026-10-23 — Qualité des commandes Olist (phase 1)

### Séparer les sources et les résultats
- Les CSV Olist de data/ sont la source historique brute. Ne pas modifier leurs valeurs, remplacer arbitrairement les dates manquantes ou supprimer les commandes signalées.
- validate_orders() travaille sur une copie du DataFrame ; conversion des dates avec errors="coerce", avec un motif invalid_* lorsque la valeur originale non nulle ne se convertit pas.
- Les sorties sous data/processed/ sont des produits dérivés régénérables, ignorés par Git. main() remplace les deux fichiers de sortie, sans modifier les CSV bruts.
- Une anomalie indique une investigation, pas une erreur définitivement confirmée ; aucune correction automatique d'une date.

### Grain et traçabilité
- Grain attendu : une commande par order_id. L'absence de doublons est vérifiée sur les 99 441 lignes auditées.
- quality_status vaut valid si aucune règle ne se déclenche, review sinon. valid n'est pas une garantie d'exactitude absolue.
- quality_issue_count compte les règles déclenchées ; quality_issues est une chaîne JSON représentant la liste des noms de règles, conservée dans le CSV.
- Les trois contrôles de date manquante visent les commandes delivered ; les comparaisons de dates concernent tous les statuts ; liste de statuts autorisés explicite dans le module.
- Une même ligne avec plusieurs anomalies compte une fois dans review_orders. Le code compte cependant des lignes, pas des order_id distincts ; sur des données dupliquées, ne pas présenter ce total comme des commandes distinctes.
- Aucun dédoublonnage implicite ni jointure items × payments. Les paiements ne sont pas automatiquement un chiffre d'affaires comptable.
- Les dates sont actuellement sans fuseau explicite. Aucune conversion UTC inventée ; documenter les conventions avant les KPI et l'ingestion.

### Exploration et pipeline
- notebooks/01_data_exploration.ipynb sert à comprendre les données ; src/validation/orders_validator.py porte la logique réutilisable, testée via validate_orders().
- Les totaux du notebook concordent, mais sa liste quality_issues reste construite avec cinq anciennes règles. Le pipeline recalculé est la référence actuelle pour les motifs ; harmonisation du notebook à autoriser séparément.
- Garder Pandas pour le volume exploré. Le code lit intégralement orders et customers ; aucun benchmark mémoire ni garantie de passage à grande échelle. Prévoir une lecture par lots si le besoin est établi.
- Ne mutualiser les helpers entre tables qu'après identification de comportements partagés ; aucun nouveau validateur customers ou service installé ici.

### Limites et reproductibilité
- Six tests actuels : deux d'environnement et quatre du validateur ; toutes les règles ne sont pas couvertes.
- Date d'achat/estimée absente déjà nulle non signalée ; doublons clients dans customers comptés sans déclencher review. Contrats et cas limites à définir avant correction.
- Pandas 3.1.0, NumPy 2.4.6 et ipykernel 7.4.0 observés dans le venv mais absents de requirements.txt. L'environnement fonctionne, sa reconstruction complète n'est pas encore garantie.
- Cette intervention est documentaire : aucun changement du code, des données, du notebook ou des dépendances ; aucun commit/push, aucun accès à D:.
- Provenance déclarée Olist Kaggle ; licence et modalités d'acquisition à consigner. Aucune réécriture de la roadmap AGENTS.md.


## 2026-10-23 — Développement sur C: (décision conservée ; bilan de phase 0 historique)

- Projet officiel : C:\Users\PC\Documents\Projets stage\ecommerce-data-platform ; conserver et utiliser exclusivement son .venv vérifié.
- Motif : octets nuls et répertoires illisibles observés dans le venv sur D:. La cause exacte n'est pas établie et la migration n'a pas été validée.
- D: exclu du développement ; ne pas accéder à ses fichiers ni les modifier, supprimer ou déplacer.
- Chemins relatifs depuis la racine ; VS Code utilise par défaut ${workspaceFolder}/.venv/Scripts/python.exe. Sélection effective à confirmer manuellement.
- Conserver Python 3.11 et requirements.txt/pip pour leur simplicité ; versions verrouillées après tests. pyproject.toml reste une alternative si le packaging devient nécessaire.
- Git existant conservé avec main, origin et la branche de sauvegarde. Synchronisation réalisée ; aucun historique recréé, reset ou force-push. Les nouveaux commits attendent validation.
- 8 Go de RAM annoncés ; 7,974 Gio libres sur C: à l'audit, à revérifier avant chaque téléchargement ou installation. Aucun service lourd requis en phase 0.
- Code et documentation sur C:, historique Git : sources de vérité actuelles. Aucun dataset ni pipeline métier. .env.example sans secret, non chargé automatiquement.
- Phase 0 clôturée documentairement ; phase 1 uniquement après accord.

## Historique — décisions du 2026-10-22

Les décisions ci-dessous sont conservées pour expliquer la tentative de migration. Elles sont remplacées par la décision du 2026-10-23 et ne constituent plus des actions à exécuter.

# Decisions phase 0 : conserver Python 3.11 et .venv. Utiliser requirements.txt/pip, plus simple que le packaging pyproject.toml pour commencer. Installer seulement pytest, verrouiller apres tests. Git local sans commit ni distant. Services lourds differes pour 8 Go RAM. Aucun dataset ni pipeline.

## 2026-10-22 - Migration vers D:
- Projet copie vers D:\DataEngineering\ecommerce-data-platform ; original sur C: conserve sans suppression.
- D: NTFS ; empreintes de 30 fichiers verifies avant adaptation, aucune difference. .git conserve.
- .venv recree sur D: ; Python de base reste installe sur C:, ce qui est normal.
- TEMP et TMP rediriges vers .migration-temp sur D: pendant installation ; pip sans cache.
- datasets/ et docker-data/ crees dans D:\DataEngineering ; Docker/WSL non modifies.
- Garder D: branche et sa lettre stable. Sauvegarder regulierement ; aucune base active sur support debranchable sans etude separee.
- VS Code : chemin relatif .venv/Scripts/python.exe configure ; selection effective a confirmer manuellement.
- Validation migration suspendue : fichiers du nouveau venv contiennent des octets nuls ; pip check et pytest echouent. Cause exacte inconnue. Garder original sur C: et diagnostiquer support/connexion avant nouvel environnement.
