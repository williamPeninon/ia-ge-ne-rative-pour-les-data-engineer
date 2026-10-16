# Specification du projet fil rouge

> A completer par le groupe, en debut de Jour 5, avant le debut de
> l'implementation (cf. planning : validation par le formateur avant 11h15).
> Tient sur une page : si ce n'est pas le cas, le perimetre est trop large.

## Groupe

- Membres :
- Cas d'usage retenu :

## Cas d'usage

(1-2 phrases : quel probleme de Data Engineer ce pipeline resout-il ?)

## Entree / sortie

- Entree :
- Sortie (schema JSON cible) :

## Architecture

- Appel API direct vs orchestration LangChain :
- Modele utilise : (par defaut, le modele auto-heberge via Ollama, cf. .env.example)
- Synchrone vs asynchrone :

## Contraintes de validation

- Regles ou schema a verifier sur la sortie :
- Gestion des erreurs / cas limites prevus :

## Criteres de succes

- (ex. taux de conformite au schema, latence maximale acceptable, etc.)

---

Rappel des contraintes du projet :

- Aucune donnee reelle ou de production BFORBANK : uniquement des donnees fictives
- Toute cle d'API est geree via variable d'environnement (voir `.env.example`), jamais en dur dans le code
- Le pipeline doit inclure une etape de validation de la sortie du LLM
- Le code reste dans le perimetre de ce depot (pas de diffusion externe)
