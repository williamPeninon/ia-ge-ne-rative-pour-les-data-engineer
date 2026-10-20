"""
TP4 - Corrige
Module 4 - Orchestration d'un pipeline LLM (Jour 2 apres-midi)

Reserve au formateur : a distribuer aux stagiaires seulement apres la
correction collective.

Pipeline : Extraction -> Nettoyage assiste par LLM -> Resume structure (JSON)
-> controle de coherence deterministe.

Mecanismes de logging (cf. logging_bancaire.md) :
  - horodatage ISO 8601 UTC sur chaque evenement
  - identifiant de correlation (run_id) propage a toutes les etapes
  - prompt et reponse : masques (IBAN, carte, email, telephone) puis tronques
  - duree, tokens (prompt / completion / total), statut et type d'erreur
  - journal d'audit JSONL (un evenement = une ligne) en plus de la console
"""
import csv
import io
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

# Chemins : la source est partagee avec l'enonce, le journal d'audit reste local au corrige.
BASE_DIR = Path(__file__).parent
SOURCE_FILE = BASE_DIR.parent / "extrait_source.txt"
# AUDIT_LOG_FILE permet de rediriger le journal (tests, autre disque) sans modifier le code.
AUDIT_FILE = Path(os.environ.get("AUDIT_LOG_FILE", BASE_DIR / "logs" / "audit_tp4.jsonl"))

MAX_LOG_CHARS = 300          # taille max d'un prompt/reponse ecrit dans les logs
MAX_TENTATIVES_JSON = 3      # regenerations si la sortie JSON est invalide
TOLERANCE_MONTANT = 0.01     # ecart accepte entre le LLM et le calcul deterministe (arrondis)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("tp4-corrige")


# --------------------------------------------------------------------------
# Logging / audit
# --------------------------------------------------------------------------
# Chaque tuple = (regex, jeton de remplacement). On masque avant d'ecrire le log
# pour ne pas persister d'IBAN, de numero de carte, d'email ou de telephone.
PATTERNS_SENSIBLES = [
    (re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b"), "[IBAN]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARTE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+33|0)\s?[1-9](?:[\s.-]?\d{2}){4}(?!\d)"), "[TEL]"),
]


def masquer_et_tronquer(texte: str, limite: int = MAX_LOG_CHARS) -> str:
    """Masque les donnees personnelles detectables puis tronque pour le log."""
    for motif, remplacement in PATTERNS_SENSIBLES:
        texte = motif.sub(remplacement, texte)
    # On garde assez de contexte pour debugger, sans stocker le prompt entier.
    if len(texte) > limite:
        return texte[:limite] + f"... [tronque, {len(texte)} caracteres]"
    return texte


def log_evenement(run_id: str, etape: str, statut: str, duree_ms: int, **champs) -> None:
    """Ecrit un evenement dans la console et dans le journal d'audit JSONL."""
    # Schema stable : timestamp UTC, correlation, etape, statut, duree, puis champs libres.
    evenement = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "run_id": run_id,
        "etape": etape,
        "statut": statut,
        "duree_ms": duree_ms,
        **champs,
    }
    # ok -> INFO, ecart de coherence -> WARNING, tout le reste (echec) -> ERROR.
    niveau = {"ok": logging.INFO, "ecart": logging.WARNING}.get(statut, logging.ERROR)
    logger.log(niveau, "run=%s etape=%s statut=%s duree_ms=%d %s",
               run_id[:8], etape, statut, duree_ms,
               " ".join(f"{k}={v}" for k, v in champs.items()))
    try:
        # JSONL : une ligne = un evenement, facile a filtrer ensuite (jq, pandas).
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evenement, ensure_ascii=False) + "\n")
    except OSError as exc:  # un probleme de journal ne doit pas casser le pipeline
        logger.warning("Ecriture du journal d'audit impossible : %s", exc)


# --------------------------------------------------------------------------
# Modele de sortie valide
# --------------------------------------------------------------------------
class ResumeStructure(BaseModel):
    """Contrat de sortie du LLM. Pydantic rejette un JSON mal type ou incomplet."""
    nb_mouvements: int = Field(ge=0)
    total_depenses: float = Field(ge=0, description="somme des debits, en valeur absolue")
    total_revenus: float = Field(ge=0, description="somme des credits")
    anomalies: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Client LLM
# --------------------------------------------------------------------------
def get_client() -> OpenAI:
    """Client compatible OpenAI : la base_url pointe vers le LLM local ou distant."""
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
    )


def appeler_llm(client: OpenAI, model: str, run_id: str, etape: str,
                messages: list[dict], **kwargs) -> str:
    """Appel LLM avec log complet : prompt, reponse, duree, tokens, statut."""
    # On masque le prompt avant l'appel : meme un echec reseau ne doit pas le logger en clair.
    prompt_log = masquer_et_tronquer(" || ".join(m["content"] for m in messages))
    start = time.perf_counter()
    try:
        # temperature basse : on veut une sortie stable, pas de la creativite.
        # kwargs laisse passer response_format (JSON force) sans dupliquer la fonction.
        reponse = client.chat.completions.create(
            model=model, temperature=0.2, messages=messages, **kwargs
        )
    except Exception as exc:
        # On journalise le type d'erreur puis on relance : l'appelant decide d'arreter.
        log_evenement(run_id, etape, "echec", int((time.perf_counter() - start) * 1000),
                      erreur=type(exc).__name__, prompt=prompt_log)
        raise
    contenu = reponse.choices[0].message.content or ""
    usage = getattr(reponse, "usage", None)
    log_evenement(
        run_id, etape, "ok", int((time.perf_counter() - start) * 1000),
        modele=model,
        tokens_prompt=getattr(usage, "prompt_tokens", None),
        tokens_completion=getattr(usage, "completion_tokens", None),
        tokens_total=getattr(usage, "total_tokens", None),
        prompt=prompt_log,
        reponse=masquer_et_tronquer(contenu),
    )
    return contenu


# --------------------------------------------------------------------------
# Etapes du pipeline
# --------------------------------------------------------------------------
def extraire_source(run_id: str) -> str:
    """Lit le CSV brut. Pas d'appel LLM : l'extraction reste deterministe."""
    start = time.perf_counter()
    try:
        texte = SOURCE_FILE.read_text(encoding="utf-8")
    except Exception as exc:
        log_evenement(run_id, "extraction", "echec", int((time.perf_counter() - start) * 1000),
                      erreur=type(exc).__name__, source=SOURCE_FILE.name)
        raise
    log_evenement(run_id, "extraction", "ok", int((time.perf_counter() - start) * 1000),
                  source=SOURCE_FILE.name, nb_lignes=len(texte.splitlines()))
    return texte


def nettoyer_assiste_par_llm(client: OpenAI, model: str, run_id: str, texte_brut: str) -> str:
    """Normalise les libelles. Les montants, dates et signes restent intacts."""
    return appeler_llm(
        client, model, run_id, "nettoyage",
        [
            {"role": "system", "content": (
                "Tu nettoies un extrait de mouvements bancaires fictifs au format CSV "
                "(ID;DATE;MONTANT;LIBELLE). Developpe les abreviations (VIR = virement, "
                "PRLV = prelevement, CB = carte bancaire) et produis une ligne lisible par "
                "mouvement, de la forme : '<ID> | <DATE> | <MONTANT> EUR | <libelle clair>'. "
                "Ne change ni les montants, ni les dates, ni les signes. N'ajoute aucun commentaire."
            )},
            {"role": "user", "content": texte_brut},
        ],
    )


def generer_resume_structure(client: OpenAI, model: str, run_id: str,
                             texte_nettoye: str) -> ResumeStructure:
    """Demande un JSON structure, puis le valide. Relance le LLM s'il est invalide."""
    messages = [
        {"role": "system", "content": (
            "Tu reponds UNIQUEMENT en JSON valide avec exactement ces champs : "
            "nb_mouvements (int), total_depenses (float positif : somme des montants negatifs "
            "en valeur absolue), total_revenus (float : somme des montants positifs), "
            "anomalies (liste de string, vide si aucune). "
            "Signale comme anomalie tout mouvement inhabituel (montant disproportionne, "
            "libelle incoherent avec le signe du montant)."
        )},
        {"role": "user", "content": texte_nettoye},
    ]
    derniere_erreur = None
    # Boucle de reparation : si le JSON est invalide, on renvoie l'erreur au modele.
    for tentative in range(1, MAX_TENTATIVES_JSON + 1):
        etape = "resume" if tentative == 1 else f"resume_retry{tentative - 1}"
        brut = appeler_llm(client, model, run_id, etape, messages,
                           response_format={"type": "json_object"})
        try:
            # Double controle : JSON parsable, puis conforme au modele Pydantic.
            return ResumeStructure.model_validate(json.loads(brut))
        except (json.JSONDecodeError, ValidationError) as exc:
            derniere_erreur = exc
            log_evenement(run_id, "validation_json", "echec", 0,
                          tentative=tentative, erreur=type(exc).__name__)
            # On ajoute la mauvaise reponse et la consigne de correction a l'historique.
            messages = messages + [
                {"role": "assistant", "content": brut},
                {"role": "user", "content": (
                    "Ta reponse n'est pas conforme au schema demande. "
                    "Reponds uniquement avec le JSON corrige."
                )},
            ]
    raise ValueError(f"Sortie JSON invalide apres {MAX_TENTATIVES_JSON} tentatives") from derniere_erreur


def calculer_reference(texte_brut: str) -> dict:
    """Calcul deterministe sur la source : sert de verite terrain au LLM."""
    # On relit le CSV d'origine, pas le texte nettoye : le LLM ne doit pas
    # pouvoir fausser la reference en modifiant un montant.
    lignes = list(csv.DictReader(io.StringIO(texte_brut), delimiter=";"))
    montants = [float(l["MONTANT"]) for l in lignes]
    return {
        "nb_mouvements": len(montants),
        # Depenses = somme des montants negatifs, ramenee en valeur positive.
        "total_depenses": round(-sum(m for m in montants if m < 0), 2),
        "total_revenus": round(sum(m for m in montants if m > 0), 2),
    }


def controler_coherence(run_id: str, resume: ResumeStructure, texte_brut: str) -> dict:
    """Compare les chiffres du LLM au calcul deterministe ; la reference fait foi."""
    start = time.perf_counter()
    ref = calculer_reference(texte_brut)
    ecarts = []
    if resume.nb_mouvements != ref["nb_mouvements"]:
        ecarts.append("nb_mouvements")
    # Tolerance sur les flottants : un centime d'ecart d'arrondi n'est pas une anomalie.
    for champ in ("total_depenses", "total_revenus"):
        if abs(getattr(resume, champ) - ref[champ]) > TOLERANCE_MONTANT:
            ecarts.append(champ)

    # On conserve les anomalies textuelles du LLM, mais on ecrase les chiffres
    # par ceux de la reference (update apres model_dump).
    resultat = resume.model_dump()
    resultat.update(ref)
    resultat["ecarts_llm_corriges"] = ecarts
    log_evenement(run_id, "controle", "ok" if not ecarts else "ecart",
                  int((time.perf_counter() - start) * 1000), ecarts=",".join(ecarts) or "aucun")
    return resultat


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def main() -> int:
    # Un UUID par execution : toutes les etapes partagent ce run_id.
    run_id = str(uuid.uuid4())
    model = os.environ.get("LLM_MODEL", "mistral")
    logger.info("Demarrage du pipeline run_id=%s modele=%s", run_id, model)
    debut = time.perf_counter()
    try:
        # Enchainement ETL : extraire -> nettoyer (LLM) -> resumer (LLM) -> controler.
        client = get_client()
        texte_brut = extraire_source(run_id)
        texte_nettoye = nettoyer_assiste_par_llm(client, model, run_id, texte_brut)
        resume = generer_resume_structure(client, model, run_id, texte_nettoye)
        # Le controle compare le resume au CSV brut, pas au texte nettoye.
        resultat = controler_coherence(run_id, resume, texte_brut)
    except Exception as exc:
        # Code de sortie 1 : un orchestrateur (Airflow, cron) peut detecter l'echec.
        log_evenement(run_id, "pipeline", "echec", int((time.perf_counter() - debut) * 1000),
                      erreur=type(exc).__name__)
        return 1
    log_evenement(run_id, "pipeline", "ok", int((time.perf_counter() - debut) * 1000))
    print(json.dumps({"run_id": run_id, **resultat}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
