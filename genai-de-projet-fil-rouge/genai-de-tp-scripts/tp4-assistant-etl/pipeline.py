"""
TP4 - Assistant generatif simulant un ETL
Module 4 - LangChain pour orchestrer les LLM (Jour 2 apres-midi)

Pipeline en 3 etapes : extraction -> nettoyage assiste par LLM -> resume
structure, avec logging a chaque etape. Vous pouvez implementer les etapes
avec LangChain OU avec de simples appels au client `openai` enchaines a la
main (les deux approches sont acceptees - cf. point de vigilance du module).
"""
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("tp4")

SOURCE_FILE = Path(__file__).parent / "extrait_source.txt"


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def log_step(nom_etape):
    """Decorateur simple : logue prompt/reponse/duree d'une etape."""
    def decorateur(fn):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                resultat = fn(*args, **kwargs)
                statut = "ok"
                return resultat
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
    # TODO : appeler le LLM pour nettoyer/normaliser le texte brut
    # (ex. transformer le CSV en phrases lisibles, corriger les libelles abreges)
    raise NotImplementedError


@log_step("resume")
def generer_resume_structure(client: OpenAI, model: str, texte_nettoye: str) -> dict:
    # TODO : appeler le LLM pour produire un resume structure en JSON
    # (ex. nombre de mouvements, total des depenses, total des revenus,
    # anomalies eventuelles) - utiliser response_format={"type": "json_object"}
    raise NotImplementedError


def main():
    client = get_client()
    model = os.environ.get("LLM_MODEL", "mistral")

    texte_brut = extraire_source()
    texte_nettoye = nettoyer_assiste_par_llm(client, model, texte_brut)
    resume = generer_resume_structure(client, model, texte_nettoye)

    logger.info("Resume final : %s", resume)


if __name__ == "__main__":
    main()
