# TP4 - Assistant generatif simulant un ETL (LangChain)

Module 4, Jour 2 apres-midi. Duree indicative : 75 min.

## Consignes

1. Concevoir, avec LangChain (ou une chaine de prompts manuelle), un mini pipeline en 3 etapes :
   extraction d'un texte source (`extrait_source.txt`), transformation/nettoyage assiste par LLM,
   generation d'un resume structure
2. Ajouter un mecanisme de logging a chaque etape (prompt envoye, reponse recue, duree)
3. Documenter les mecanismes de logging necessaires dans un contexte de production bancaire
   (tracabilite, audit) - voir le fichier `logging_bancaire.md` a completer

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
python pipeline.py
```

Le fichier `extrait_source.txt` est un extrait fictif de mouvements bancaires
(aucune donnee reelle) a utiliser comme entree du pipeline.

Completez les `# TODO` dans `pipeline.py`, puis `logging_bancaire.md`.
