# Garantir l'absence de donnees reelles dans le dataset genere (corrige)

- Consigne explicite dans le prompt : rappeler que toutes les personnes sont fictives et qu'aucune ne doit correspondre a une personne reelle connue, meme par coincidence
- Controle croise avec une liste noire de noms connus (si disponible) : comparer les noms/prenoms generes a une liste de collaborateurs reels de l'entreprise, rejeter/regenerer en cas de correspondance
- Relecture humaine par sondage : verifier manuellement un echantillon du jeu genere avant utilisation
- Interdiction d'exemples few-shot issus de donnees reelles : ne jamais fournir au modele un exemple d'enregistrement reel en few-shot, meme partiel ou anonymise
