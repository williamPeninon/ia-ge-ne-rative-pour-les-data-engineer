# TP5 - Generation d'un dataset RH conforme RGPD

Module 5, Jour 3 matin. Duree indicative : 70 min.

## Consignes

1. Definir un schema de donnees RH (matricule, nom, prenom, date de naissance, poste,
   departement, date d'entree) - voir `schema.py`
2. Rediger un prompt de generation produisant N enregistrements respectant ce schema,
   avec des valeurs realistes mais entierement fictives
3. Verifier la coherence des donnees generees (types, plages de valeurs, unicite du matricule)
4. Documenter comment garantir qu'aucune donnee reelle ne s'est glissee dans le jeu genere
   (voir `garanties_rgpd.md` a completer)

## Demarrage

```bash
pip install -r requirements.txt
cp .env.example .env
python generer_dataset.py
```

Completez les `# TODO` dans `generer_dataset.py`.
