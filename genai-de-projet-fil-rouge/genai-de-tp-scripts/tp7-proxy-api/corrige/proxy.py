"""
TP7 - Corrige
Module 7 - Securiser et industrialiser l'usage de l'IA generative (Jour 4 matin)

Reserve au formateur : a distribuer aux stagiaires seulement apres la
demonstration collective.

Proxy applicatif place entre l'application et l'API du LLM :

    Application -> Filtre d'entree -> Proxy/Gateway -> API LLM -> Filtre de sortie -> Application

  Filtre d'entree : longueur maximale, mots-cles interdits (injection,
                    identifiants, marquages de confidentialite), donnees
                    personnelles (IBAN, carte, NIR : bloquees ; email,
                    telephone : masquees avant envoi)
  Gateway         : attribution de chaque appel (equipe + usage), quota de
                    tokens par equipe, plafond de tokens de reponse, timeout
  Filtre de sortie: memes controles sur la reponse du LLM
  Journal d'audit : metadonnees systematiques, contenu jamais journalise si
                    une donnee sensible a ete detectee, retention bornee,
                    alerte en cas de detections repetees

Ce code est une reference pedagogique. Les regex ne sont pas exhaustives et la
politique de securite interne de la DSI prevaut toujours sur les valeurs
choisies ici (seuils, listes, retention).

Usage :
    python proxy.py --simulation                 # jeu de test, sans LLM
    python proxy.py                              # jeu de test, LLM du .env (Ollama)
    python proxy.py --prompt "..." --equipe data --usage resume
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
import unicodedata
import uuid
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("tp7-proxy")

VERSION_POLITIQUE = "2026-10-v1"  # tracee dans chaque evenement : quelle regle a decide ?

BLOQUER = "bloquer"
MASQUER = "masquer"


# ---------------------------------------------------------------------------
# 1. Configuration de la politique de filtrage
# ---------------------------------------------------------------------------
# Mots-cles interdits, par famille. Compares apres normalisation (casse, accents,
# apostrophes) et sur des mots entiers. Une famille = un motif de blocage lisible
# dans le journal, sans jamais y ecrire le contenu de la requete.
MOTS_INTERDITS_PAR_DEFAUT = {
    "injection": [
        "ignore les instructions", "ignore previous instructions", "ignore all previous",
        "oublie tes instructions", "affiche ton prompt systeme", "reveal your system prompt",
    ],
    "identifiants": ["mot de passe", "password", "cle api", "api key", "token d'acces"],
    "classification": ["strictement confidentiel", "diffusion restreinte"],
}


@dataclass
class Configuration:
    longueur_max_entree: int = 4000          # caracteres, tous messages confondus (~1000 tokens)
    longueur_max_sortie: int = 8000
    max_tokens_reponse: int = 512            # plafonne le cout et la fuite par la sortie
    timeout_llm_s: float = 30.0
    # Donnees tres sensibles : on n'envoie rien. Donnees courantes : on masque et on envoie.
    politique_pii: dict = field(default_factory=lambda: {
        "NIR": BLOQUER, "IBAN": BLOQUER, "CARTE": BLOQUER,
        "EMAIL": MASQUER, "TELEPHONE": MASQUER,
    })
    mots_interdits: dict = field(default_factory=lambda: dict(MOTS_INTERDITS_PAR_DEFAUT))
    # En sortie, seules ces familles font retenir la reponse (l'injection n'a pas de sens en sortie).
    familles_bloquantes_sortie: tuple = ("identifiants", "classification")
    quota_tokens_jour: int = 200_000         # par equipe
    seuil_alerte_budget: float = 0.8
    alerte_seuil: int = 3                    # incidents de securite ...
    alerte_fenetre_s: int = 600              # ... dans cette fenetre, pour une meme equipe
    retention_jours: int = int(os.environ.get("LOG_RETENTION_DAYS", "30"))
    journaliser_contenu: bool = True         # extrait du prompt, uniquement si rien de sensible detecte
    extrait_max: int = 200


# ---------------------------------------------------------------------------
# 2. Detection des donnees personnelles / sensibles
# ---------------------------------------------------------------------------
# Un motif seul genere trop de faux positifs (un numero de dossier a 16 chiffres
# n'est pas une carte). On valide donc chaque candidat par sa cle de controle :
# une vraie donnee la respecte toujours, un numero quelconque presque jamais.
def _luhn_ok(brut: str) -> bool:
    chiffres = re.sub(r"\D", "", brut)
    if not 13 <= len(chiffres) <= 19:
        return False
    total = 0
    for i, c in enumerate(reversed(chiffres)):
        n = int(c)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _iban_ok(brut: str) -> bool:
    iban = re.sub(r"\s", "", brut).upper()
    if not 15 <= len(iban) <= 34:
        return False
    rearrange = iban[4:] + iban[:4]
    # Lettres -> nombres (A=10 ... Z=35), puis controle modulo 97 (ISO 13616).
    return int("".join(str(int(c, 36)) for c in rearrange)) % 97 == 1


def _nir_ok(brut: str) -> bool:
    nir = re.sub(r"[ .]", "", brut).upper()
    if len(nir) != 15:
        return False
    corps, cle = nir[:13].replace("2A", "19").replace("2B", "18"), nir[13:]
    if not (corps.isdigit() and cle.isdigit()):
        return False
    return 97 - int(corps) % 97 == int(cle)  # cle de controle du numero de securite sociale


# Ordre = priorite en cas de chevauchement (un NIR de 15 chiffres peut aussi ressembler a une carte).
_DETECTEURS = [
    ("NIR", re.compile(r"(?<![\dA-Z])[12](?:[ .]?\d{2}){2}[ .]?(?:\d{2}|2[AB])[ .]?\d{3}[ .]?\d{3}[ .]?\d{2}(?![\dA-Z])",
                       re.IGNORECASE), _nir_ok),
    ("IBAN", re.compile(r"(?<![A-Z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?(?![A-Z0-9])",
                        re.IGNORECASE), _iban_ok),
    ("CARTE", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), _luhn_ok),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None),
    ("TELEPHONE", re.compile(r"(?<!\d)(?:(?:\+|00)33[\s.-]?|0)[1-9](?:[\s.-]?\d{2}){4}(?!\d)"), None),
]


@dataclass(frozen=True)
class Detection:
    """Position d'une donnee sensible. La valeur n'est volontairement PAS conservee :
    ainsi elle ne peut pas finir dans un log par erreur."""
    categorie: str
    debut: int
    fin: int


def detecter_pii(texte: str) -> list:
    retenues = []
    for categorie, motif, valide in _DETECTEURS:
        for m in motif.finditer(texte):
            if valide and not valide(m.group()):
                continue
            if any(m.start() < r.fin and r.debut < m.end() for r in retenues):
                continue  # deja couvert par un detecteur plus prioritaire
            retenues.append(Detection(categorie, m.start(), m.end()))
    return sorted(retenues, key=lambda d: d.debut)


def masquer(texte: str, detections: list) -> str:
    # De la fin vers le debut, pour que les positions restent valables.
    for d in sorted(detections, key=lambda d: d.debut, reverse=True):
        texte = texte[:d.debut] + f"[{d.categorie}]" + texte[d.fin:]
    return texte


# ---------------------------------------------------------------------------
# 3. Mots-cles interdits
# ---------------------------------------------------------------------------
def _normaliser(texte: str) -> str:
    """Minuscules, sans accents, apostrophes unifiees, espaces compactes."""
    decompose = unicodedata.normalize("NFKD", texte)
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sans_accents.casefold().replace("’", "'"))


def _compiler_mots(mots_par_famille: dict) -> dict:
    return {
        famille: re.compile(r"(?<!\w)(?:" + "|".join(re.escape(_normaliser(m)) for m in mots) + r")(?!\w)")
        for famille, mots in mots_par_famille.items()
    }


def detecter_mots_interdits(texte: str, motifs: dict, familles=None) -> list:
    """Renvoie les familles detectees (jamais les mots : ils pourraient etre sensibles)."""
    normalise = _normaliser(texte)
    return [f for f, motif in motifs.items()
            if (familles is None or f in familles) and motif.search(normalise)]


# ---------------------------------------------------------------------------
# 4. Journal d'audit : contenu minimal, retention bornee
# ---------------------------------------------------------------------------
class JournalAudit:
    """JSONL, un fichier par jour UTC (audit-AAAA-MM-JJ.jsonl).

    Un fichier par jour rend la retention triviale et sure : purger = supprimer
    les fichiers de plus de N jours, sans jamais reecrire un journal existant.
    """

    def __init__(self, dossier: Path, retention_jours: int,
                 horloge: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.dossier = Path(dossier)
        self.retention_jours = retention_jours
        self._horloge = horloge
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.purger()

    def ecrire(self, evenement: dict) -> bool:
        maintenant = self._horloge()
        evenement = {"timestamp": maintenant.isoformat(timespec="milliseconds"), **evenement}
        fichier = self.dossier / f"audit-{maintenant:%Y-%m-%d}.jsonl"
        try:
            # 0o600 : lisible par le seul compte de service (le journal reste une donnee sensible).
            fd = os.open(fichier, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(json.dumps(evenement, ensure_ascii=False) + "\n")
            return True
        except OSError as exc:
            # Choix a arbitrer avec la DSI : ici on ne coupe pas le service, mais l'echec est visible.
            logger.error("Ecriture du journal d'audit impossible : %s", type(exc).__name__)
            return False

    def purger(self) -> list:
        """Supprime les journaux plus anciens que la retention. Renvoie les fichiers supprimes."""
        limite = self._horloge().date() - timedelta(days=self.retention_jours)
        supprimes = []
        for fichier in self.dossier.glob("audit-*.jsonl"):
            try:
                jour = date.fromisoformat(fichier.stem.removeprefix("audit-"))
            except ValueError:
                continue
            if jour < limite:
                fichier.unlink()
                supprimes.append(fichier.name)
        return supprimes


# ---------------------------------------------------------------------------
# 5. Alerting et quotas
# ---------------------------------------------------------------------------
class SuiviIncidents:
    """Alerte quand une equipe cumule trop d'incidents de securite dans une fenetre glissante."""

    def __init__(self, seuil: int, fenetre_s: int, horloge: Callable[[], float] = time.monotonic):
        self.seuil, self.fenetre_s, self._horloge = seuil, fenetre_s, horloge
        self._evenements = defaultdict(deque)
        self._derniere_alerte = {}

    def enregistrer(self, equipe: str) -> Optional[int]:
        """Renvoie le nombre d'incidents si une alerte doit partir, sinon None."""
        maintenant = self._horloge()
        file = self._evenements[equipe]
        file.append(maintenant)
        while file and maintenant - file[0] > self.fenetre_s:
            file.popleft()
        recent = maintenant - self._derniere_alerte.get(equipe, float("-inf")) < self.fenetre_s
        if len(file) >= self.seuil and not recent:  # une alerte par fenetre, pas une par appel
            self._derniere_alerte[equipe] = maintenant
            return len(file)
        return None


class QuotaTokens:
    """Budget quotidien de tokens par equipe (en memoire ; en production : Redis/base)."""

    def __init__(self, plafond: int, horloge: Callable[[], date] = lambda: datetime.now(timezone.utc).date()):
        self.plafond, self._horloge = plafond, horloge
        self._conso = {}  # equipe -> (jour, tokens)

    def consommation(self, equipe: str) -> int:
        jour, total = self._conso.get(equipe, (self._horloge(), 0))
        return total if jour == self._horloge() else 0

    def disponible(self, equipe: str, estimation: int) -> bool:
        return self.consommation(equipe) + estimation <= self.plafond

    def ajouter(self, equipe: str, tokens: int) -> float:
        total = self.consommation(equipe) + tokens
        self._conso[equipe] = (self._horloge(), total)
        return total / self.plafond


# ---------------------------------------------------------------------------
# 6. Le proxy
# ---------------------------------------------------------------------------
@dataclass
class ReponseProxy:
    request_id: str
    statut: str  # ok | ok_masque | bloque_entree | bloque_sortie | quota_depasse | requete_invalide | erreur_llm
    contenu: Optional[str]
    motifs: list
    revue_humaine: bool = False  # reponse alteree par le filtre : relecture avant tout usage


class ProxyLLM:
    def __init__(self, client, modele: str, config: Configuration = None, journal: JournalAudit = None,
                 alerteur: Callable[[dict], None] = None, quota: QuotaTokens = None,
                 suivi: SuiviIncidents = None):
        self.client, self.modele = client, modele
        self.config = config or Configuration()
        self.journal = journal or JournalAudit(
            Path(os.environ.get("PROXY_AUDIT_DIR", Path(__file__).parent / "logs")), self.config.retention_jours)
        self.quota = quota or QuotaTokens(self.config.quota_tokens_jour)
        self.suivi = suivi or SuiviIncidents(self.config.alerte_seuil, self.config.alerte_fenetre_s)
        self.alerteur = alerteur or (lambda alerte: logger.critical("ALERTE SECURITE %s", json.dumps(alerte)))
        self._motifs = _compiler_mots(self.config.mots_interdits)
        self._budget_alerte = set()

    # -- filtres ------------------------------------------------------------
    def filtre_entree(self, messages: list):
        """Renvoie (bloque, messages_a_envoyer, motifs, compteur_pii)."""
        cfg, motifs, pii = self.config, [], Counter()
        if sum(len(m["content"]) for m in messages) > cfg.longueur_max_entree:
            # On refuse au lieu de tronquer (couper change le sens) et on n'analyse pas
            # un texte demesure : cela evite qu'un envoi geant ne sature le proxy.
            return True, messages, ["longueur_max_depassee"], pii
        bloque, nettoyes = False, []
        for message in messages:
            texte = message["content"]
            detections = detecter_pii(texte)
            for d in detections:
                pii[d.categorie] += 1
                if cfg.politique_pii.get(d.categorie, BLOQUER) == BLOQUER:  # categorie inconnue : prudence
                    bloque = True
                    motifs.append(f"pii_bloquante:{d.categorie}")
            for famille in detecter_mots_interdits(texte, self._motifs):
                bloque = True
                motifs.append(f"mot_interdit:{famille}")
            nettoyes.append({**message, "content": masquer(texte, detections)})
        if not bloque and pii:
            motifs.append("pii_masquee_en_entree")
        return bloque, nettoyes, list(dict.fromkeys(motifs)), pii

    def filtre_sortie(self, texte: str):
        """Renvoie (bloque, texte_a_renvoyer, motifs, compteur_pii)."""
        cfg, motifs = self.config, []
        if len(texte) > cfg.longueur_max_sortie:
            texte = texte[:cfg.longueur_max_sortie]
            motifs.append("sortie_tronquee")
        familles = detecter_mots_interdits(texte, self._motifs, cfg.familles_bloquantes_sortie)
        if familles:
            return True, None, motifs + [f"mot_interdit_sortie:{f}" for f in familles], Counter()
        detections = detecter_pii(texte)  # toute donnee sensible en sortie est masquee, jamais renvoyee
        if detections:
            motifs.append("sortie_pii_masquee")
        return False, masquer(texte, detections), motifs, Counter(d.categorie for d in detections)

    # -- appel --------------------------------------------------------------
    def completer_prompt(self, prompt: str, **kw) -> ReponseProxy:
        return self.completer([{"role": "user", "content": prompt}], **kw)

    def completer(self, messages: list, *, equipe: str, usage: str, utilisateur: str = None) -> ReponseProxy:
        debut = time.perf_counter()
        request_id = str(uuid.uuid4())
        evt = {
            "type": "appel", "request_id": request_id, "equipe": (equipe or "")[:64],
            "usage": (usage or "")[:64], "utilisateur": self._pseudonyme(utilisateur),
            "modele": self.modele, "version_politique": VERSION_POLITIQUE,
        }
        # 0. Chaque appel doit etre attribuable a une equipe ET a un usage.
        valide = (equipe and usage and isinstance(messages, list) and messages
                  and all(isinstance(m, dict) and isinstance(m.get("content"), str) for m in messages))
        if not valide:
            return self._clore(evt, debut, "requete_invalide", ["equipe_usage_ou_messages_invalides"])
        evt["longueur_prompt"] = sum(len(m["content"]) for m in messages)

        # 1. Filtre d'entree.
        bloque, a_envoyer, motifs, pii_entree = self.filtre_entree(messages)
        evt["pii_entree"] = dict(pii_entree)
        evt["prompt_sha256"] = hashlib.sha256(
            "\n".join(m["content"] for m in a_envoyer).encode("utf-8")).hexdigest()  # version masquee
        if bloque:
            return self._clore(evt, debut, "bloque_entree", motifs)
        # Le contenu n'est journalise que si rien de sensible n'a ete vu (jamais de PII dans les logs).
        if self.config.journaliser_contenu and not pii_entree:
            evt["extrait_prompt"] = a_envoyer[-1]["content"][:self.config.extrait_max]

        # 2. Quota de l'equipe (estimation prudente : ~3 caracteres par token).
        estimation = evt["longueur_prompt"] // 3 + self.config.max_tokens_reponse
        if not self.quota.disponible(equipe, estimation):
            return self._clore(evt, debut, "quota_depasse", ["quota_tokens_equipe"])

        # 3. Appel du LLM : message d'erreur jamais journalise (il peut contenir le prompt).
        try:
            reponse = self.client.chat.completions.create(
                model=self.modele, messages=a_envoyer, temperature=0.2,
                max_tokens=self.config.max_tokens_reponse, timeout=self.config.timeout_llm_s)
            contenu = reponse.choices[0].message.content or ""
        except Exception as exc:
            return self._clore(evt, debut, "erreur_llm", [f"erreur_llm:{type(exc).__name__}"])
        usage_llm = getattr(reponse, "usage", None)
        tokens = getattr(usage_llm, "total_tokens", None) or estimation  # repli : l'estimation
        evt.update(tokens_prompt=getattr(usage_llm, "prompt_tokens", None),
                   tokens_completion=getattr(usage_llm, "completion_tokens", None),
                   tokens_total=tokens, longueur_reponse=len(contenu))
        self._suivre_budget(equipe, self.quota.ajouter(equipe, tokens))

        # 4. Filtre de sortie.
        bloque_sortie, contenu_final, motifs_sortie, pii_sortie = self.filtre_sortie(contenu)
        evt["pii_sortie"] = dict(pii_sortie)
        if bloque_sortie:
            return self._clore(evt, debut, "bloque_sortie", motifs + motifs_sortie, revue_humaine=True)
        statut = "ok_masque" if (pii_entree or pii_sortie) else "ok"
        return self._clore(evt, debut, statut, motifs + motifs_sortie, contenu_final,
                           revue_humaine=bool(motifs_sortie))

    # -- utilitaires ----------------------------------------------------------
    @staticmethod
    def _pseudonyme(utilisateur: Optional[str]) -> Optional[str]:
        """Identifiant utilisateur pseudonymise : retrouvable pour un audit, pas lisible dans le log."""
        if not utilisateur:
            return None
        sel = os.environ.get("LOG_HASH_SALT", "")
        return hashlib.sha256((sel + utilisateur).encode("utf-8")).hexdigest()[:12]

    def _suivre_budget(self, equipe: str, ratio: float) -> None:
        cle = (datetime.now(timezone.utc).date(), equipe)
        if ratio >= self.config.seuil_alerte_budget and cle not in self._budget_alerte:
            self._budget_alerte.add(cle)
            self._alerter({"type": "alerte", "nature": "budget_tokens", "equipe": equipe,
                           "ratio_consomme": round(ratio, 2)})

    def _alerter(self, alerte: dict) -> None:
        self.journal.ecrire(alerte)
        self.alerteur(alerte)

    def _clore(self, evt: dict, debut: float, statut: str, motifs: list,
               contenu: str = None, revue_humaine: bool = False) -> ReponseProxy:
        evt.update(statut=statut, motifs=motifs, revue_humaine=revue_humaine,
                   duree_ms=int((time.perf_counter() - debut) * 1000))
        self.journal.ecrire(evt)
        logger.info("request=%s equipe=%s statut=%s motifs=%s", evt["request_id"][:8], evt["equipe"],
                    statut, ",".join(motifs) or "-")
        incident = bool(evt.get("pii_entree") or evt.get("pii_sortie")
                        or any(m.startswith("mot_interdit") for m in motifs))
        if incident and evt["equipe"]:
            nb = self.suivi.enregistrer(evt["equipe"])
            if nb:
                self._alerter({"type": "alerte", "nature": "detections_sensibles_repetees",
                               "equipe": evt["equipe"], "incidents": nb,
                               "fenetre_s": self.config.alerte_fenetre_s})
        return ReponseProxy(evt["request_id"], statut, contenu, motifs, revue_humaine)


# ---------------------------------------------------------------------------
# 7. Demonstration
# ---------------------------------------------------------------------------
class ClientSimule:
    """Faux LLM (meme interface que le client openai) pour travailler hors VM."""

    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    @staticmethod
    def _create(*, model, messages, **_):
        dernier = messages[-1]["content"]
        if "[[FUITE_MDP]]" in dernier:
            texte = "Voici le mot de passe administrateur : Xk9!"
        elif "[[FUITE_PII]]" in dernier:
            texte = "Contactez Marie Durand : marie.durand@example.com ou 06 12 34 56 78."
        else:
            texte = f"Reponse simulee ({len(dernier)} caracteres recus) : {dernier[:60]}"
        usage = SimpleNamespace(prompt_tokens=len(dernier) // 3 + 1, completion_tokens=len(texte) // 3 + 1)
        usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=texte))], usage=usage)


def charger_cas(chemin: Path) -> list:
    cas = json.loads(Path(chemin).read_text(encoding="utf-8"))
    for c in cas:
        if "prompt_repete" in c:  # evite un fichier de 5 000 caracteres
            c["prompt"] = c["prompt_repete"]["motif"] * c["prompt_repete"]["fois"]
    return cas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TP7 - proxy de securisation d'appels LLM")
    parser.add_argument("--simulation", action="store_true", help="faux LLM (aucun appel reseau)")
    parser.add_argument("--prompt", help="envoyer un seul prompt")
    parser.add_argument("--equipe", default="equipe-data")
    parser.add_argument("--usage", default="demo")
    parser.add_argument("--cas", default=str(Path(__file__).parent.parent / "prompts_test.json"))
    args = parser.parse_args(argv)

    if args.simulation:
        client, modele = ClientSimule(), "simulation"
    else:
        from dotenv import load_dotenv  # imports ici : la simulation n'exige ni openai ni .env
        from openai import OpenAI
        load_dotenv()
        # La cle vient de l'environnement uniquement : jamais dans le code, jamais dans les logs.
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"])
        modele = os.environ.get("LLM_MODEL", "mistral")
    proxy = ProxyLLM(client, modele)

    if args.prompt:
        r = proxy.completer_prompt(args.prompt, equipe=args.equipe, usage=args.usage)
        print(json.dumps(r.__dict__, ensure_ascii=False, indent=2))
        return 0

    ecarts = 0
    print(f"{'cas':<24}{'attendu':<18}{'obtenu':<18}{'verdict':<8}motifs")
    for c in charger_cas(args.cas):
        r = proxy.completer_prompt(c["prompt"], equipe=c.get("equipe", ""), usage=c.get("usage", ""),
                                   utilisateur=c.get("utilisateur"))
        ok = r.statut == c["attendu"]
        ecarts += not ok
        print(f"{c['id']:<24}{c['attendu']:<18}{r.statut:<18}{'OK' if ok else 'ECART':<8}{', '.join(r.motifs) or '-'}")
    print(f"\n{ecarts} ecart(s) sur le jeu de test. Journal : {proxy.journal.dossier}/")
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
