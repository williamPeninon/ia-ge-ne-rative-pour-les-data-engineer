# Squelettes TP3 / TP4 / TP5 / TP6

Scripts autonomes pour les travaux pratiques codes des Jours 2 et 3
(independants du projet fil rouge du Jour 5). Le LLM est deja auto-heberge
sur votre VM (Ollama, cf. fiche de besoin VM) : ces scripts s'y connectent
directement, pas besoin de docker ici.

## Mise en place (une seule fois)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r <tp>/requirements.txt   # ex. pip install -r tp3-appel-llm/requirements.txt
cp <tp>/.env.example <tp>/.env
```

Chaque dossier de TP a son propre `requirements.txt` et `.env.example` (les
dependances different legerement d'un TP a l'autre). Le `.env` pointe vers le
LLM local :

```
OPENAI_API_KEY=ollama-local
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=mistral
```

## Contenu

| Dossier | TP | Jour / Module |
| --- | --- | --- |
| `tp3-appel-llm/` | TP3 : script Python pour interroger un LLM | Jour 2 matin - Module 3 |
| `tp4-assistant-etl/` | TP4 : assistant generatif simulant un ETL (LangChain) | Jour 2 apres-midi - Module 4 |
| `tp5-dataset-rh/` | TP5 : generation d'un dataset RH conforme RGPD | Jour 3 matin - Module 5 |
| `tp6-evaluation-qualite/` | TP6 : evaluation qualite d'un dataset genere (metriques, anomalies, actions correctives) | Jour 3 apres-midi - Module 6 |

Chaque dossier contient un script avec des `# TODO` a completer : ce sont des
squelettes, pas des corriges. Chaque TP a aussi un sous-dossier `corrige/` avec
la solution complete - **reserve au formateur**, a ne distribuer aux stagiaires
qu'apres la correction collective de chaque TP.
