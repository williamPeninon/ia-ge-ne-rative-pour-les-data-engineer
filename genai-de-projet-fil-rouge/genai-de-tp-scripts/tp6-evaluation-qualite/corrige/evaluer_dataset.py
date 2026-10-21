"""
TP6 - Corrige
Module 6 - Evaluation de la qualite de sortie (Jour 3 apres-midi)

Reserve au formateur : a distribuer aux stagiaires seulement apres la
correction collective.

Principe : la qualite d'une sortie generee ne se juge pas "au feeling". On
definit 3 metriques mesurables (conformite de schema, plausibilite des
valeurs, absence de doublons), on les calcule en code deterministe, on isole
les enregistrements suspects et on associe une action corrective a chaque
anomalie. Un enregistrement qui echoue n'est jamais integre tel quel au jeu
final (filtre de rejet) : il est rejete ou regenere de facon ciblee.

Usage :
    python evaluer_dataset.py                      # evalue ../jeu_secours.json
    python evaluer_dataset.py mon_dataset.json     # evalue le jeu du TP5
    python evaluer_dataset.py --regenerer          # + regeneration ciblee via le LLM
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

# Le schema est partage avec l'enonce (dossier parent), pas duplique dans le corrige.
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import RH_DATASET_SCHEMA, RH_RECORD_SCHEMA

DATASET_PAR_DEFAUT = Path(__file__).parent.parent / "jeu_secours.json"

# --- Les 3 metriques -------------------------------------------------------
CONFORMITE = "conformite_schema"
PLAUSIBILITE = "plausibilite"
UNICITE = "unicite"

# Seuils d'acceptation (part d'enregistrements sans anomalie pour la metrique).
# Definis AVANT de generer : schema et unicite sont stricts, la plausibilite
# tolere un faible taux d'ecart statistique.
SEUILS = {CONFORMITE: 1.0, PLAUSIBILITE: 0.95, UNICITE: 1.0}

# --- Bornes de plausibilite ------------------------------------------------
AGE_ENTREE_MIN = 16  # en dessous : pas d'embauche (hors alternance, a affiner)
AGE_ENTREE_MAX = 70
DATE_ENTREE_MIN = date(1980, 1, 1)

# Lettres (accents compris), mots separes par espace, tiret ou apostrophe.
# Rejette 'Xyz123', '###', '' ... mais accepte "Jean-Pierre" ou "O'Brien".
_MOT = r"[A-Za-zÀ-ÖØ-öø-ÿ]+"
REGEX_NOM = re.compile(rf"^{_MOT}(?:[ '\-]{_MOT})*$")

# --- Regles : metrique, type d'action, action corrective proposee ----------
# "regenerer" : on redemande l'enregistrement au LLM (regeneration ciblee)
# "rejeter"   : on l'ecarte du jeu final (filtre de rejet)
REGLES = {
    "schema_champ_manquant": (CONFORMITE, "regenerer",
        "Regenerer l'enregistrement en rappelant le schema complet (champs obligatoires) dans le prompt"),
    "schema_type": (CONFORMITE, "regenerer",
        "Regenerer l'enregistrement ; rappeler les types attendus et garder response_format JSON"),
    "matricule_format": (CONFORMITE, "regenerer",
        "Appliquer la regex ^M[0-9]{5}$ avant integration ; regeneration ciblee de l'enregistrement"),
    "date_format": (CONFORMITE, "regenerer",
        "Valider le format de date (AAAA-MM-JJ, date reelle du calendrier) ; regeneration ciblee"),
    "schema_autre": (CONFORMITE, "regenerer",
        "Regenerer l'enregistrement et corriger le prompt si l'erreur se repete"),
    "nom_incoherent": (PLAUSIBILITE, "regenerer",
        "Ajouter une regle de validation (regex lettres / tiret / apostrophe) ; regeneration ciblee"),
    "prenom_incoherent": (PLAUSIBILITE, "regenerer",
        "Ajouter une regle de validation (regex lettres / tiret / apostrophe) ; regeneration ciblee"),
    "champ_texte_invalide": (PLAUSIBILITE, "regenerer",
        "Exiger un texte non vide et non numerique pour poste/departement ; regeneration ciblee"),
    "dates_incoherentes": (PLAUSIBILITE, "regenerer",
        "Regle metier date_naissance < date_entree ; regeneration ciblee en rappelant la contrainte"),
    "age_entree_invraisemblable": (PLAUSIBILITE, "regenerer",
        "Regle de plage sur l'age a l'embauche (16-70 ans) ; regeneration ciblee"),
    "date_entree_hors_plage": (PLAUSIBILITE, "regenerer",
        "Regle de plage sur date_entree (pas dans le futur, pas avant 1980) ; regeneration ciblee"),
    "matricule_duplique": (UNICITE, "regenerer",
        "Garder la 1re occurrence, regenerer la suivante en interdisant les matricules deja pris "
        "(l'unicite est garantie par le code, pas par le LLM)"),
    "personne_dupliquee": (UNICITE, "rejeter",
        "Rejeter le doublon (filtre de rejet) ; pour plus de diversite : temperature plus haute, "
        "ou noms tires d'une liste/Faker"),
}


def _anomalie(index: int, employe, regle: str, detail: str) -> dict:
    metrique, action, correctif = REGLES[regle]
    matricule = employe.get("matricule", "?") if isinstance(employe, dict) else "?"
    return {
        "index": index,
        "matricule": matricule,
        "regle": regle,
        "metrique": metrique,
        "action": action,
        "detail": detail,
        "correctif": correctif,
    }


def charger_employes(chemin: Path) -> list:
    """Charge le JSON ({"employes": [...]} comme au TP5, ou liste directe)."""
    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if isinstance(contenu, list):
        return contenu
    if isinstance(contenu, dict) and isinstance(contenu.get("employes"), list):
        return contenu["employes"]
    raise ValueError("format inattendu : attendu une liste ou {\"employes\": [...]}")


def _date_valide(valeur):
    """Renvoie une date, ou None si la valeur n'est pas une date AAAA-MM-JJ reelle."""
    try:
        return date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Metrique 1 : conformite de schema
# ---------------------------------------------------------------------------
# FormatChecker : sans lui, jsonschema ignore "format": "date" et laisserait
# passer une date comme 1975-13-40.
_VALIDATEUR = Draft7Validator(RH_RECORD_SCHEMA, format_checker=FormatChecker())


def controler_conformite(employes: list) -> list:
    anomalies = []
    for i, e in enumerate(employes):
        for erreur in _VALIDATEUR.iter_errors(e):
            champ = ".".join(str(p) for p in erreur.absolute_path) or "(enregistrement)"
            if erreur.validator == "required":
                regle = "schema_champ_manquant"
            elif erreur.validator == "type":
                regle = "schema_type"
            elif erreur.validator == "pattern" and champ == "matricule":
                regle = "matricule_format"
            elif erreur.validator == "format":
                regle = "date_format"
            else:
                regle = "schema_autre"
            anomalies.append(_anomalie(i, e, regle, f"{champ} : {erreur.message}"))
    return anomalies


# ---------------------------------------------------------------------------
# Metrique 2 : plausibilite des valeurs
# ---------------------------------------------------------------------------
def controler_plausibilite(employes: list, aujourd_hui: date = None) -> list:
    aujourd_hui = aujourd_hui or date.today()
    anomalies = []
    for i, e in enumerate(employes):
        if not isinstance(e, dict):
            continue  # deja signale par la conformite

        # Noms incoherents (chiffres, symboles, vide) : typique d'une hallucination.
        for champ in ("nom", "prenom"):
            valeur = e.get(champ)
            if isinstance(valeur, str) and not REGEX_NOM.match(valeur.strip()):
                anomalies.append(_anomalie(i, e, f"{champ}_incoherent",
                                           f"{champ} = {valeur!r} : caracteres inattendus ou vide"))

        for champ in ("poste", "departement"):
            valeur = e.get(champ)
            if isinstance(valeur, str) and (not valeur.strip() or valeur.strip().isdigit()):
                anomalies.append(_anomalie(i, e, "champ_texte_invalide",
                                           f"{champ} = {valeur!r} : vide ou numerique"))

        # Une date mal formee est deja signalee par la conformite : on ne la reevalue pas.
        naissance = _date_valide(e.get("date_naissance"))
        entree = _date_valide(e.get("date_entree"))

        if entree and (entree > aujourd_hui or entree < DATE_ENTREE_MIN):
            anomalies.append(_anomalie(i, e, "date_entree_hors_plage",
                                       f"date_entree = {entree} hors de [{DATE_ENTREE_MIN}, {aujourd_hui}]"))

        if naissance and entree:
            if naissance >= entree:
                anomalies.append(_anomalie(i, e, "dates_incoherentes",
                                           f"date_naissance {naissance} posterieure ou egale a date_entree {entree}"))
            else:
                # 365.25 approxime les annees bissextiles.
                age = (entree - naissance).days / 365.25
                if not AGE_ENTREE_MIN <= age <= AGE_ENTREE_MAX:
                    anomalies.append(_anomalie(i, e, "age_entree_invraisemblable",
                                               f"age a l'entree = {age:.0f} ans (plage {AGE_ENTREE_MIN}-{AGE_ENTREE_MAX})"))
    return anomalies


# ---------------------------------------------------------------------------
# Metrique 3 : absence de doublons
# ---------------------------------------------------------------------------
def _cle_identite(e: dict) -> tuple:
    # casefold + strip : "DUBOIS " et "dubois" designent la meme personne.
    return tuple(str(e.get(c, "")).strip().casefold() for c in ("nom", "prenom", "date_naissance"))


def controler_unicite(employes: list) -> list:
    """On signale les occurrences APRES la premiere : la 1re reste dans le jeu."""
    anomalies = []
    matricules = {}
    identites = {}
    for i, e in enumerate(employes):
        if not isinstance(e, dict):
            continue

        matricule = e.get("matricule")
        if isinstance(matricule, str):
            if matricule in matricules:
                anomalies.append(_anomalie(i, e, "matricule_duplique",
                                           f"matricule {matricule} deja utilise par l'enregistrement #{matricules[matricule]}"))
            else:
                matricules[matricule] = i

        cle = _cle_identite(e)
        if all(cle):  # on ne compare que des identites completes
            if cle in identites:
                anomalies.append(_anomalie(i, e, "personne_dupliquee",
                                           f"meme nom/prenom/date de naissance que l'enregistrement #{identites[cle]}"))
            else:
                identites[cle] = i
    return anomalies


# ---------------------------------------------------------------------------
# Evaluation globale et filtre de rejet
# ---------------------------------------------------------------------------
def evaluer(employes: list) -> dict:
    """Calcule les 3 metriques et renvoie un rapport."""
    anomalies = (
        controler_conformite(employes)
        + controler_plausibilite(employes)
        + controler_unicite(employes)
    )
    total = len(employes)

    metriques = {}
    for nom in (CONFORMITE, PLAUSIBILITE, UNICITE):
        fautifs = {a["index"] for a in anomalies if a["metrique"] == nom}
        taux = 1 - len(fautifs) / total if total else 0.0
        metriques[nom] = {
            "taux": round(taux, 4),
            "seuil": SEUILS[nom],
            "ok": total > 0 and taux >= SEUILS[nom],
            "enregistrements_en_anomalie": len(fautifs),
        }

    suspects = sorted({a["index"] for a in anomalies})
    return {
        "total": total,
        "metriques": metriques,
        "indices_suspects": suspects,
        "taux_enregistrements_valides": round(1 - len(suspects) / total, 4) if total else 0.0,
        "accepte": total > 0 and all(m["ok"] for m in metriques.values()),
        "anomalies": anomalies,
    }


def filtrer(employes: list, rapport: dict):
    """Filtre de rejet : separe les enregistrements valides des rejetes."""
    suspects = set(rapport["indices_suspects"])
    valides = [e for i, e in enumerate(employes) if i not in suspects]
    rejets = [
        {
            "index": i,
            "enregistrement": employes[i],
            "anomalies": [a for a in rapport["anomalies"] if a["index"] == i],
        }
        for i in rapport["indices_suspects"]
    ]
    return valides, rejets


# ---------------------------------------------------------------------------
# Regeneration ciblee (optionnelle, necessite le LLM)
# ---------------------------------------------------------------------------
def _demander_candidat(client, model: str, rejet: dict, valides: list):
    """Redemande UN employe au LLM en lui donnant les raisons du rejet."""
    raisons = "; ".join(a["detail"] for a in rejet["anomalies"])
    matricules_pris = [e["matricule"] for e in valides]
    reponse = client.chat.completions.create(
        model=model,
        temperature=0.8,
        messages=[
            {"role": "system", "content": (
                "Tu generes des jeux de donnees RH entierement fictifs. Aucune personne ne doit "
                "correspondre a une personne reelle. Tu reponds UNIQUEMENT en JSON valide "
                "respectant exactement ce schema : " + json.dumps(RH_DATASET_SCHEMA))},
            {"role": "user", "content": (
                f"Genere 1 seul employe fictif. Le precedent a ete rejete pour : {raisons}. "
                f"Matricule au format M + 5 chiffres, different de : {matricules_pris}. "
                "Nom et prenom composes uniquement de lettres, date_naissance anterieure a "
                "date_entree, age a l'embauche entre 16 et 70 ans, date_entree dans le passe.")},
        ],
        response_format={"type": "json_object"},
    )
    try:
        employes = json.loads(reponse.choices[0].message.content).get("employes")
        return employes[0] if employes else None
    except (json.JSONDecodeError, AttributeError, TypeError, IndexError):
        return None


def regenerer_rejets(client, model: str, valides: list, rejets: list, max_essais: int = 3):
    """Regenere chaque enregistrement rejete. Renvoie (jeu complete, rejets definitifs).

    Un candidat n'est integre que s'il passe a son tour les 3 metriques : le LLM
    n'est jamais cru sur parole. Apres max_essais echecs, l'enregistrement reste rejete.
    """
    jeu = list(valides)
    definitifs = []
    for rejet in rejets:
        for _ in range(max_essais):
            candidat = _demander_candidat(client, model, rejet, jeu)
            # `jeu` est propre : le test ne peut echouer qu'a cause du candidat.
            if candidat is not None and not evaluer(jeu + [candidat])["anomalies"]:
                jeu.append(candidat)
                break
        else:
            definitifs.append(rejet)
    return jeu, definitifs


# ---------------------------------------------------------------------------
# Affichage / sortie
# ---------------------------------------------------------------------------
def afficher_rapport(rapport: dict, employes: list):
    print(f"=== Rapport qualite : {rapport['total']} enregistrements ===")
    for nom, m in rapport["metriques"].items():
        statut = "OK" if m["ok"] else "KO"
        print(f"  {nom:<18} {m['taux']:>7.1%}  (seuil {m['seuil']:.0%})  {statut}"
              f"  - {m['enregistrements_en_anomalie']} enregistrement(s) en anomalie")
    print(f"  enregistrements valides : {rapport['taux_enregistrements_valides']:.1%}")
    print(f"  verdict : {'JEU ACCEPTE' if rapport['accepte'] else 'JEU REFUSE en l etat'}")

    if rapport["indices_suspects"]:
        print(f"\n=== Enregistrements suspects ({len(rapport['indices_suspects'])}) ===")
    for i in rapport["indices_suspects"]:
        print(f"\n#{i} {employes[i].get('matricule', '?') if isinstance(employes[i], dict) else '?'}")
        for a in (x for x in rapport["anomalies"] if x["index"] == i):
            print(f"  - [{a['metrique']}] {a['regle']} : {a['detail']}")
            print(f"      -> {a['action']} : {a['correctif']}")


def ecrire_json(chemin: Path, contenu):
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="TP6 - evaluation qualite d'un dataset RH genere")
    parser.add_argument("chemin", nargs="?", default=str(DATASET_PAR_DEFAUT), help="dataset JSON a evaluer")
    parser.add_argument("--sortie", default="sortie", help="dossier des fichiers produits")
    parser.add_argument("--regenerer", action="store_true", help="regenerer les rejets via le LLM")
    parser.add_argument("--max-essais", type=int, default=3)
    args = parser.parse_args()

    employes = charger_employes(Path(args.chemin))
    rapport = evaluer(employes)
    afficher_rapport(rapport, employes)

    valides, rejets = filtrer(employes, rapport)

    if args.regenerer and rejets:
        # Imports ici : le controle qualite seul ne necessite ni openai ni .env.
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv()
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"])
        modele = os.environ.get("LLM_MODEL", "mistral")
        valides, rejets = regenerer_rejets(client, modele, valides, rejets, args.max_essais)
        print(f"\nApres regeneration ciblee : {len(valides)} valides, {len(rejets)} rejet(s) definitif(s).")

    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    ecrire_json(sortie / "rapport_qualite.json", rapport)
    ecrire_json(sortie / "dataset_valide.json", {"employes": valides})
    ecrire_json(sortie / "dataset_rejets.json", rejets)
    print(f"\nFichiers ecrits dans {sortie}/ : rapport_qualite.json, dataset_valide.json, dataset_rejets.json")


if __name__ == "__main__":
    main()
