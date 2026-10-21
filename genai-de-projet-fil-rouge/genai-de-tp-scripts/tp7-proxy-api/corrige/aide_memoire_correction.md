# TP7 - Aide-mémoire formateur (1 page, 20 min)

Détail et phrases complètes : `discours_correction.md`.

## Chronomètre

| Min | Partie | À faire |
| --- | --- | --- |
| 0-2 | Ouverture | Question : « qu'est-ce qui empêche de coller un IBAN dans un prompt ? » + la DSI prévaut |
| 2-5 | Schéma | Un binôme redessine : App → Filtre entrée → Proxy → LLM → Filtre sortie → App |
| 5-11 | Règles d'entrée | Longueur · mots interdits · données sensibles |
| 11-15 | Logging | Logger / masquer / ne pas logger · rétention · alerting |
| 15-18 | Démo | `proxy.py --simulation`, journal, tests, 1 prompt de la salle |
| 18-20 | Bilan | 4 idées + transition module 8 |

## Les messages clés

- **Schéma** : le proxy est le seul à avoir la clé · chaque appel = équipe + usage · le journal est transverse
- **Entrée** : refuser, ne pas tronquer · mots normalisés (casse, accents, mots entiers)
- **Bloquer** IBAN, carte, NIR · **masquer** email, téléphone (minimisation)
- **Clé de contrôle** : Luhn (carte), modulo 97 (IBAN), clé NIR → pas de faux positifs sur un n° de dossier
- **Piège** « pourquoi pas le LLM pour détecter ? » → il faudrait lui envoyer la donnée
- **Sortie** : masquer + `revue_humaine` ; retenir si mot de passe / « strictement confidentiel »
- **Logging** : un journal mal pensé = un second stockage de données personnelles

## Logging en un coup d'œil

| Toujours | Pseudonymiser / catégories seules | Jamais |
| --- | --- | --- |
| horodatage, request_id, équipe, usage, modèle, statut, motifs, durée, tokens | utilisateur (hash salé) · « 1 IBAN » sans la valeur · hash du prompt masqué | contenu d'une requête où du sensible a été vu · réponse du LLM · clé d'API · erreur brute du fournisseur |

Rétention **30 j** (exemple, valeur réelle = DSI/DPO) · purge auto · alerte **3 détections / 10 min / équipe** · budget **80 %**

## Démo (dans `corrige/`)

```bash
python proxy.py --simulation          # 12 cas attendu/obtenu
cat logs/audit-*.jsonl | head -3      # ce qu'on enregistre
grep -c "@" logs/audit-*.jsonl        # 0
python -m unittest test_proxy         # 27 tests OK
python proxy.py --simulation --prompt "Virement vers FR76 3000 6000 0112 3456 7890 189"
```
Cas à commenter : `faux_positif_dossier` (16 chiffres qui passent) · `fuite_pii_sortie` (masqué + relecture)

## Bilan (4 idées)

1. Un point de passage unique
2. Bloquer l'interdit, masquer le reste
3. Ne jamais journaliser ce qu'on a protégé
4. Un humain dans la boucle · l'ingénieur signe la chaîne

## Limites à avouer

Pas de noms propres ni d'adresses · un filtre se contourne · seuils = arbitrage faux positifs/négatifs · quotas en mémoire

## Si on te demande…

LLM local donc pourquoi filtrer ? → minimisation, journaux, réutilisation · Filtre en panne ? → fail-closed vs fail-open, à décider avec la DSI · AI Act ? → dépend du niveau de risque, renvoyer vers conformité

## Avant / après

☐ 12 cas OK · ☐ 27 tests OK · ☐ supprimer `corrige/logs/` après la démo · ☐ distribuer `corrige/` seulement après
