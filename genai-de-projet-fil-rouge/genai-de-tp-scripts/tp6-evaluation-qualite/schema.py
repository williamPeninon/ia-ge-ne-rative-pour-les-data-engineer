"""Schema du dataset RH fictif a generer (TP5, reutilise au TP6)."""

RH_RECORD_SCHEMA = {
    "type": "object",
    "properties": {
        "matricule": {"type": "string", "pattern": "^M[0-9]{5}$"},
        "nom": {"type": "string"},
        "prenom": {"type": "string"},
        "date_naissance": {"type": "string", "format": "date"},
        "poste": {"type": "string"},
        "departement": {"type": "string"},
        "date_entree": {"type": "string", "format": "date"},
    },
    "required": [
        "matricule", "nom", "prenom", "date_naissance",
        "poste", "departement", "date_entree",
    ],
}

RH_DATASET_SCHEMA = {
    "type": "object",
    "properties": {
        "employes": {"type": "array", "items": RH_RECORD_SCHEMA},
    },
    "required": ["employes"],
}
