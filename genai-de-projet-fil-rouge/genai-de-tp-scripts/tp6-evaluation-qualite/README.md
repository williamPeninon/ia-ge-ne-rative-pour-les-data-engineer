# TP6 - Evaluation qualite d'un output genere

Module 6, Jour 3 apres-midi. Duree indicative : 70 min.

## Consignes

1. Reprendre le jeu de donnees RH genere au TP5 (ou le jeu fourni : `jeu_secours.json`)
2. Definir 3 metriques de qualite : conformite de schema, plausibilite des valeurs,
   absence de doublons
3. Identifier les enregistrements suspects (noms incoherents, valeurs hors plage, doublons)
4. Proposer une action corrective pour chaque anomalie detectee
   (voir `actions_correctives.md` a completer)

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
python evaluer_dataset.py                    # evalue jeu_secours.json
python evaluer_dataset.py mon_dataset.json   # evalue votre jeu du TP5
```

Le script du TP5 n'enregistre pas son resultat : pour evaluer votre propre jeu, ajoutez
a la fin de son `main()` :

```python
with open("dataset_rh.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)
```

`jeu_secours.json` est un jeu fictif (aucune donnee reelle) qui contient volontairement
des anomalies : utilisez-le si vous n'avez pas termine le TP5.

Completez les `# TODO` dans `evaluer_dataset.py`, puis `actions_correctives.md`.
