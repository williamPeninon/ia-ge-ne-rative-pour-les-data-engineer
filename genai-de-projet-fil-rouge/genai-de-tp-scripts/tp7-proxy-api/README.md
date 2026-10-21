# TP7 - Mise en place d'un proxy API avec filtrage des entrees

Module 7, Jour 4 matin. Duree indicative : 70 min.

## Consignes

1. Concevoir (schema ou pseudo-code) un proxy applicatif s'interposant entre l'application
   et l'API du LLM
2. Definir les regles de filtrage a appliquer sur les entrees : detection de donnees
   personnelles/sensibles avant envoi, longueur maximale, liste de mots-cles interdits
3. Definir le niveau de logging a mettre en place : quoi logger, quoi masquer, duree de retention

Le livrable principal est `conception_proxy.md` (schema, regles, logging). `proxy.py` est un
squelette facultatif pour mettre vos regles a l'epreuve sur `prompts_test.json`.

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
python proxy.py            # applique votre filtre d'entree aux prompts de test (sans appel LLM)
```

`prompts_test.json` contient des prompts **fictifs** (aucune donnee reelle) : un prompt propre,
des donnees personnelles, des mots interdits, un prompt trop long, une tentative d'injection...
Chaque cas indique le statut `attendu` du filtre d'entree.

Completez `conception_proxy.md`, puis les `# TODO` dans `proxy.py`.
