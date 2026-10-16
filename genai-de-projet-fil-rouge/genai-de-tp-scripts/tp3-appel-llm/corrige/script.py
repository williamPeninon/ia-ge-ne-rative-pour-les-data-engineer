"""
TP3 - Corrige
Module 3 - Manipulation de LLM avec Python (Jour 2 matin)

Reservé au formateur : a distribuer aux stagiaires seulement apres la
correction collective (point de vigilance du programme).
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

    # 1. Prompt simple
    reponse = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Explique en une phrase ce qu'est un pipeline de donnees."}],
    )
    print("1. Reponse simple :", reponse.choices[0].message.content)

    # 2. Effet de la temperature sur des appels repetes
    prompt_repete = "Donne un synonyme du mot 'rapide'."
    print("\n2. Effet de la temperature :")
    for temperature in (0.0, 0.9):
        print(f"  temperature={temperature}")
        for _ in range(3):
            r = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt_repete}],
            )
            print("   ->", r.choices[0].message.content.strip())
    # A temperature basse (0-0.2), les appels repetes donnent des reponses quasi
    # identiques ; a temperature elevee (0.8-1), les reponses varient davantage.

    # 3. Sortie structuree en JSON (extraction d'entites)
    reponse_json = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Tu extrais des entites et repond UNIQUEMENT en JSON valide."},
            {"role": "user", "content": "Jean Dupont, ne le 12/05/1985, habite a Lyon."},
        ],
        response_format={"type": "json_object"},
    )
    donnees = json.loads(reponse_json.choices[0].message.content)
    print("\n3. Entites extraites :", donnees)

    # 4. Prompt ambigu ou incomplet
    reponse_ambigue = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Et pour celui-ci ?"}],
    )
    print("\n4. Reponse a un prompt incomplet :", reponse_ambigue.choices[0].message.content)
    # Le modele produit quand meme une reponse plausible mais non fiable
    # (hallucination d'un contexte absent), ou une sortie qui ne respecte pas
    # le format demande - d'ou la necessite de valider systematiquement la
    # sortie (schema JSON, regeneration si echec).


if __name__ == "__main__":
    main()
