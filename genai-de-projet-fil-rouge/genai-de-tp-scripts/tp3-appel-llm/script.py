"""
TP3 - Script Python pour interroger un LLM
Module 3 - Manipulation de LLM avec Python (Jour 2 matin)

Le LLM est auto-heberge (Ollama) : voir .env.example pour l'endpoint.
Completez les TODO ci-dessous.
"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def main():
    client = get_client()
    model = os.environ.get("LLM_MODEL", "mistral")

    # TODO 1 : envoyer un prompt simple et afficher la reponse
    # response = client.chat.completions.create(
    #     model=model,
    #     messages=[{"role": "user", "content": "Votre prompt ici"}],
    # )
    # print(response.choices[0].message.content)

    # TODO 2 : rejouer le meme prompt plusieurs fois avec temperature=0.0 puis
    #          temperature=0.9, et comparer les reponses obtenues (sont-elles
    #          identiques ? varient-elles ?)

    # TODO 3 : demander une sortie structuree en JSON (ex. extraction d'entites
    #          nommees dans une phrase) en ajoutant
    #          response_format={"type": "json_object"} a l'appel, puis parser
    #          le resultat avec json.loads(...)

    # TODO 4 : tester un prompt volontairement ambigu ou incomplet et observer
    #          le comportement du modele (hallucine-t-il une reponse plausible
    #          mais non fiable ?)


if __name__ == "__main__":
    main()
