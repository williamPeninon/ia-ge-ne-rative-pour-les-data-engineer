"""
TP5 - Corrige
Module 5 - Generation de donnees synthetiques (Jour 3 matin)

Reservé au formateur : a distribuer aux stagiaires seulement apres la
correction collective.
"""
import json
import os
import re
from datetime import date

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import RH_DATASET_SCHEMA

load_dotenv()

N_ENREGISTREMENTS = 10


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def generer_dataset(client: OpenAI, model: str, n: int) -> dict:
    system_prompt = (
        "Tu generes des jeux de donnees RH entierement fictifs pour un environnement de "
        "formation. Toutes les personnes generees sont fictives : aucune ne doit "
        "correspondre a une personne reelle connue, meme par coincidence plausible. "
        "Tu reponds UNIQUEMENT en JSON valide respectant exactement ce schema : "
        + json.dumps(RH_DATASET_SCHEMA)
    )
    user_prompt = (
        f"Genere {n} employes fictifs, avec matricule au format M suivi de 5 chiffres "
        "(unique pour chaque employe), nom/prenom plausibles mais inventes, poste et "
        "departement varies, date_naissance anterieure a date_entree."
    )

    reponse = client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(reponse.choices[0].message.content)


def verifier_coherence(dataset: dict) -> list:
    anomalies = []

    try:
        validate(instance=dataset, schema=RH_DATASET_SCHEMA)
    except ValidationError as exc:
        anomalies.append(f"non conforme au schema : {exc.message}")
        return anomalies

    employes = dataset.get("employes", [])

    matricules = [e["matricule"] for e in employes]
    doublons = {m for m in matricules if matricules.count(m) > 1}
    if doublons:
        anomalies.append(f"matricules dupliques : {sorted(doublons)}")

    for e in employes:
        try:
            naissance = date.fromisoformat(e["date_naissance"])
            entree = date.fromisoformat(e["date_entree"])
            if naissance >= entree:
                anomalies.append(f"{e['matricule']} : date_naissance posterieure ou egale a date_entree")
            age_entree = (entree - naissance).days / 365.25
            if age_entree < 16 or age_entree > 70:
                anomalies.append(f"{e['matricule']} : age a l'entree invraisemblable ({age_entree:.0f} ans)")
        except (KeyError, ValueError):
            anomalies.append(f"{e.get('matricule', '?')} : date invalide")

        if not re.match(r"^M[0-9]{5}$", e.get("matricule", "")):
            anomalies.append(f"{e.get('matricule')} : format de matricule invalide")

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
