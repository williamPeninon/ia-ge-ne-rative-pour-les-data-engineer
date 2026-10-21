"""
TP6 - Evaluation qualite d'un output genere
Module 6 - Evaluation de la qualite de sortie (Jour 3 apres-midi)

Entree : un jeu de donnees RH (TP5 ou jeu_secours.json).
Sortie : des metriques, la liste des enregistrements suspects et une action
corrective par anomalie.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

from schema import RH_RECORD_SCHEMA

DATASET_PAR_DEFAUT = Path(__file__).parent / "jeu_secours.json"


def charger_employes(chemin: Path) -> list:
    """Charge le JSON et renvoie la liste des employes."""
    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    return contenu["employes"] if isinstance(contenu, dict) else contenu


def controler_conformite(employes: list) -> list:
    """Metrique 1 : conformite de schema. Renvoie une liste d'anomalies."""
    anomalies = []
    # TODO : valider chaque enregistrement avec RH_RECORD_SCHEMA
    #        (pensez au FormatChecker pour verifier les dates et au pattern du matricule)
    return anomalies


def controler_plausibilite(employes: list) -> list:
    """Metrique 2 : plausibilite des valeurs. Renvoie une liste d'anomalies."""
    anomalies = []
    # TODO : detecter les noms/prenoms incoherents (ex. 'Xyz123'), les champs vides,
    #        date_naissance >= date_entree, age a l'embauche invraisemblable,
    #        date d'entree dans le futur
    return anomalies


def controler_unicite(employes: list) -> list:
    """Metrique 3 : absence de doublons. Renvoie une liste d'anomalies."""
    anomalies = []
    # TODO : detecter les matricules dupliques et les personnes en double
    #        (meme nom + prenom + date de naissance sous un autre matricule)
    return anomalies


def main():
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else DATASET_PAR_DEFAUT
    employes = charger_employes(chemin)

    anomalies = (
        controler_conformite(employes)
        + controler_plausibilite(employes)
        + controler_unicite(employes)
    )

    # TODO : calculer un taux par metrique (enregistrements sans anomalie / total)
    # TODO : afficher les enregistrements suspects et l'action corrective proposee
    print(f"{len(employes)} enregistrements evalues, {len(anomalies)} anomalies.")


if __name__ == "__main__":
    main()
