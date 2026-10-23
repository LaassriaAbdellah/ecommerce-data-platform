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
