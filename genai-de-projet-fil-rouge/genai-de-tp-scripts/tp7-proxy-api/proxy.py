"""
TP7 - Proxy API avec filtrage des entrees
Module 7 - Securiser et industrialiser l'usage de l'IA generative (Jour 4 matin)

Squelette facultatif : le livrable principal est conception_proxy.md. Ici, vous
implementez le filtre d'entree et verifiez ses decisions sur prompts_test.json
(aucun appel au LLM necessaire).
"""
import json
import re
from pathlib import Path

CAS_DE_TEST = Path(__file__).parent / "prompts_test.json"

LONGUEUR_MAX = 4000  # caracteres : a justifier dans conception_proxy.md
MOTS_INTERDITS = []  # TODO : lister vos mots-cles interdits (injection, identifiants, ...)


def detecter_donnees_sensibles(texte: str) -> list:
    """Renvoie la liste des categories de donnees sensibles detectees (ex. ['EMAIL'])."""
    categories = []
    # TODO : detecter au minimum email, telephone, IBAN, numero de carte
    #        (une regex seule genere des faux positifs : que pouvez-vous ajouter ?)
    return categories


def masquer(texte: str) -> str:
    """Remplace les donnees sensibles par un jeton ([EMAIL], ...)."""
    # TODO
    return texte


def filtrer_entree(prompt: str, equipe: str, usage: str) -> tuple:
    """Renvoie (decision, motifs) avec decision dans {'ok', 'ok_masque', 'bloque_entree',
    'requete_invalide'}."""
    # TODO : appliquer vos regles dans cet ordre
    #   1. attribution (equipe et usage renseignes)
    #   2. longueur maximale
    #   3. mots-cles interdits
    #   4. donnees sensibles : qu'est-ce qu'on bloque ? qu'est-ce qu'on masque ?
    return "ok", []


def main():
    cas = json.loads(CAS_DE_TEST.read_text(encoding="utf-8"))
    for c in cas:
        if "prompt_repete" in c:
            c["prompt"] = c["prompt_repete"]["motif"] * c["prompt_repete"]["fois"]
        decision, motifs = filtrer_entree(c["prompt"], c.get("equipe", ""), c.get("usage", ""))
        # Les cas 'fuite_*' concernent le filtre de sortie : ignores dans ce squelette.
        if c["id"].startswith("fuite_"):
            continue
        verdict = "OK" if decision == c["attendu"] else "ECART"
        print(f"{c['id']:<24} attendu={c['attendu']:<18} obtenu={decision:<18} {verdict}")


if __name__ == "__main__":
    main()
