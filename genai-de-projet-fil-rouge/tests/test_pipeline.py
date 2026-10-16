"""
Squelette de tests - Projet fil rouge (Jour 5)

Le projet pedagogique impose : au moins 3 cas de test, dont 1 cas limite
ou un prompt adverse (cf. docs/specification_template.md). Completez les
TODO ci-dessous en fonction de votre cas d'usage.
"""
import pytest

from src.pipeline import OUTPUT_SCHEMA, validate_output


def test_sortie_conforme_au_schema():
    # TODO: remplacer par un exemple de sortie LLM valide pour votre cas d'usage
    sortie_valide = {"resultat": "exemple"}
    assert validate_output(sortie_valide) is True


def test_sortie_non_conforme_rejetee():
    sortie_invalide = {}  # champ requis manquant
    assert validate_output(sortie_invalide) is False


def test_cas_limite_ou_prompt_adverse():
    # TODO: cas limite attendu par la grille d'evaluation du projet
    # (ex. entree vide, prompt ambigu, tentative d'injection de consigne)
    pytest.skip("A completer : cas limite / prompt adverse specifique au cas d'usage")
