"""
TP4 - Corrige
Module 4 - LangChain pour orchestrer les LLM (Jour 2 apres-midi)

Reservé au formateur : a distribuer aux stagiaires seulement apres la
correction collective.

Pipeline attendu : Extraction -> Prompt de nettoyage -> Prompt de resume
structure -> sortie JSON validee, avec un log par etape.
"""
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("tp4-corrige")

SOURCE_FILE = Path(__file__).parent.parent / "extrait_source.txt"


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def log_step(nom_etape):
    def decorateur(fn):
        def wrapper(*args, **kwargs):
            start = time.time()
            statut = "ok"
            try:
                return fn(*args, **kwargs)
            except Exception:
                statut = "echec"
                raise
            finally:
                duree_ms = int((time.time() - start) * 1000)
                logger.info("etape=%s statut=%s duree_ms=%d", nom_etape, statut, duree_ms)
        return wrapper
    return decorateur


@log_step("extraction")
def extraire_source() -> str:
    return SOURCE_FILE.read_text(encoding="utf-8")


@log_step("nettoyage")
def nettoyer_assiste_par_llm(client: OpenAI, model: str, texte_brut: str) -> str:
    reponse = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": (
                "Tu nettoies un extrait de mouvements bancaires fictifs au format CSV : "
                "developpe les abreviations (VIR, PRLV, CB) en texte lisible, une ligne par mouvement."
            )},
            {"role": "user", "content": texte_brut},
        ],
    )
    return reponse.choices[0].message.content


@log_step("resume")
def generer_resume_structure(client: OpenAI, model: str, texte_nettoye: str) -> dict:
    reponse = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": (
                "Tu reponds UNIQUEMENT en JSON valide avec les champs : "
                "nb_mouvements (int), total_depenses (float), total_revenus (float), "
                "anomalies (liste de string)."
            )},
            {"role": "user", "content": texte_nettoye},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(reponse.choices[0].message.content)


def main():
    client = get_client()
    model = os.environ.get("LLM_MODEL", "mistral")

    texte_brut = extraire_source()
    texte_nettoye = nettoyer_assiste_par_llm(client, model, texte_brut)
    resume = generer_resume_structure(client, model, texte_nettoye)

    logger.info("Resume final : %s", resume)


if __name__ == "__main__":
    main()
