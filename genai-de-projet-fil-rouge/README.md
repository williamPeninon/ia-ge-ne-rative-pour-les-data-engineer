# Projet fil rouge - Jour 5

Squelette technique pour le projet fil rouge de la formation « L'IA generative
pour les Data Engineers » (BFORBANK). Il fournit un environnement pret a
l'emploi avec un LLM **auto-heberge** (Ollama) expose sur un endpoint
compatible OpenAI : le meme code `openai`/`langchain` que celui vu en Jour 2
fonctionne ici sans aucune cle API cloud.

Voir le document « Projet pedagogique » remis separement pour le contexte, les
livrables attendus et la grille d'evaluation.

## Demarrage

1. Copier le fichier d'environnement :
   ```bash
   cp .env.example .env
   ```
2. Lancer les conteneurs :
   ```bash
   docker compose up -d --build
   ```
3. Telecharger le modele (une seule fois) :
   ```bash
   ./scripts/pull_model.sh
   ```
4. Ouvrir un shell dans l'environnement de travail :
   ```bash
   docker compose exec workspace bash
   ```
5. Verifier que tout fonctionne :
   ```bash
   python src/pipeline.py
   ```

## Structure du depot

| Chemin | Contenu |
| --- | --- |
| `docker-compose.yml` | Service `ollama` (LLM auto-heberge) + service `workspace` (Python) |
| `Dockerfile` | Image de l'environnement de travail (Python 3.11 + dependances) |
| `requirements.txt` | Bibliotheques Python (openai, langchain, pydantic, jsonschema, faker, pandas) |
| `.env.example` | Variables d'environnement (endpoint LLM local, modele) |
| `src/pipeline.py` | Squelette du pipeline : appel LLM, validation, logging |
| `tests/test_pipeline.py` | Squelette de tests (schema, cas limite / prompt adverse) |
| `docs/specification_template.md` | Gabarit de la specification a rendre en debut de Jour 5 |
| `scripts/pull_model.sh` | Telechargement du modele Ollama |

## A faire par chaque groupe

1. Completer `docs/specification_template.md` (cas d'usage, schema d'entree/sortie, contraintes)
2. Adapter `OUTPUT_SCHEMA` et les prompts dans `src/pipeline.py`
3. Completer les tests dans `tests/test_pipeline.py` (au moins 3 cas, dont 1 cas limite ou un prompt adverse)
4. Mesurer le cout/latence n'a plus de sens en euros avec un LLM local : mesurer la **latence** sur le jeu de test
5. Preparer la presentation de 10 minutes (demonstration live possible directement depuis cet environnement)

## Rappels

- Aucune donnee reelle ou de production BFORBANK : uniquement des donnees fictives
- Aucune cle API cloud a gerer : le LLM tourne localement via Ollama
- Le code reste dans le perimetre de ce depot
