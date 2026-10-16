"""
TP5 - Generation d'un dataset RH conforme RGPD
Module 5 - Generation de donnees synthetiques (Jour 3 matin)

Le LLM est auto-heberge (Ollama) : voir .env.example pour l'endpoint.
"""
import json
import os

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

from schema import RH_DATASET_SCHEMA

load_dotenv()

N_ENREGISTREMENTS = 10


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def generer_dataset(client: OpenAI, model: str, n: int) -> dict:
    # TODO : rediger le prompt de generation. Il doit :
    #  - rappeler le schema attendu (champs, formats)
    #  - demander explicitement n enregistrements fictifs
    #  - insister sur le fait qu'aucune personne ne doit correspondre a une
    #    personne reelle, meme par coincidence plausible
    #  - demander une sortie JSON respectant RH_DATASET_SCHEMA
    system_prompt = "A completer"
    user_prompt = f"A completer (generer {n} employes fictifs)"

    response = client.chat.completions.create(
        model=model,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def verifier_coherence(dataset: dict) -> list:
    """Retourne la liste des anomalies trouvees (liste vide = tout est coherent)."""
    anomalies = []

    try:
        validate(instance=dataset, schema=RH_DATASET_SCHEMA)
    except ValidationError as exc:
        anomalies.append(f"non conforme au schema : {exc.message}")
        return anomalies

    # TODO : verifier l'unicite des matricules
    # TODO : verifier que date_naissance est bien anterieure a date_entree
    # TODO : verifier que les valeurs restent dans des plages plausibles

    return anomalies


def main():
    client = get_client()
    model = os.environ.get("LLM_MODEL", "mistral")

    dataset = generer_dataset(client, model, N_ENREGISTREMENTS)
    anomalies = verifier_coherence(dataset)

    if anomalies:
        print("Anomalies detectees :")
        for a in anomalies:
            print(f" - {a}")
    else:
        print(f"Dataset de {len(dataset.get('employes', []))} employes genere et valide.")


if __name__ == "__main__":
    main()
