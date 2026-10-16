#!/usr/bin/env bash
# Telecharge le modele LLM dans le conteneur Ollama (a executer une seule fois,
# apres "docker compose up -d", avant de commencer le projet).
set -euo pipefail

MODEL="${LLM_MODEL:-mistral}"

echo "Telechargement du modele '${MODEL}' dans le conteneur Ollama..."
docker compose exec ollama ollama pull "${MODEL}"
echo "OK : modele '${MODEL}' pret."
