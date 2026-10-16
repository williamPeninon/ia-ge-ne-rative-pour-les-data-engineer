# TP3 - Script Python pour interroger un LLM

Module 3, Jour 2 matin. Duree indicative : 60 min.

## Consignes

1. Ecrire un script Python qui envoie un prompt a l'API du LLM et affiche la reponse
2. Parametrer la temperature et observer l'effet sur des appels repetes avec le meme prompt
3. Demander une sortie structuree en JSON (ex. extraction d'entites d'un texte) et la parser avec le module `json`
4. Tester volontairement un prompt ambigu ou incomplet et observer le comportement du modele

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
python script.py
```

Completez les `# TODO` dans `script.py`.
