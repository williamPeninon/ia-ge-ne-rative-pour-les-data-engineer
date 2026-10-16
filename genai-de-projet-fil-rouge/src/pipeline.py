"""
Squelette du pipeline - Projet fil rouge (Jour 5)
Formation "L'IA generative pour les Data Engineers" - BFORBANK

Ce script illustre la structure attendue : appel au LLM auto-heberge (Ollama,
endpoint compatible OpenAI), validation de la sortie, logging minimal.
A completer / adapter selon le cas d'usage choisi par le groupe.
"""
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# 1. Client LLM (pointe vers Ollama via docker-compose, endpoint compatible OpenAI)
# ---------------------------------------------------------------------------
def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


# ---------------------------------------------------------------------------
# 2. Schema de sortie attendu (A ADAPTER au cas d'usage du groupe)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        # TODO: definir les champs attendus en sortie du LLM pour votre cas d'usage
        "resultat": {"type": "string"},
    },
    "required": ["resultat"],
}


# ---------------------------------------------------------------------------
# 3. Appel LLM + logging
# ---------------------------------------------------------------------------
def call_llm(client: OpenAI, system_prompt: str, user_prompt: str) -> dict:
    model = os.environ.get("LLM_MODEL", "mistral")
    start = time.time()
    status = "ok"
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception:
        status = "echec"
        raise
    finally:
        duree_ms = int((time.time() - start) * 1000)
        logger.info(
            "appel_llm model=%s statut=%s duree_ms=%d prompt_len=%d",
            model, status, duree_ms, len(user_prompt),
        )


# ---------------------------------------------------------------------------
# 4. Validation de la sortie (obligatoire : cf. contraintes du projet)
# ---------------------------------------------------------------------------
def validate_output(data: dict) -> bool:
    try:
        validate(instance=data, schema=OUTPUT_SCHEMA)
        return True
    except ValidationError as exc:
        logger.warning("validation_echec: %s", exc.message)
        return False


# ---------------------------------------------------------------------------
# 5. Point d'entree
# ---------------------------------------------------------------------------
def main():
    client = get_client()

    # TODO: remplacer par le prompt systeme / utilisateur de votre cas d'usage
    system_prompt = "Tu reponds UNIQUEMENT en JSON valide respectant le schema fourni."
    user_prompt = "Exemple de requete a adapter."

    data = call_llm(client, system_prompt, user_prompt)
    if not validate_output(data):
        logger.error("Sortie non conforme au schema, pipeline interrompu.")
        return

    logger.info("Sortie validee : %s", data)


if __name__ == "__main__":
    main()
