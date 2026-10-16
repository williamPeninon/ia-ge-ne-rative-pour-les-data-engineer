# Mecanismes de logging a prevoir en contexte bancaire (corrige)

- Horodatage de chaque appel : systematique, format ISO 8601, horloge serveur (NTP synchronisee)
- Identifiant de requete / correlation : un UUID genere en debut de pipeline, propage a chaque etape, pour tracer un appel de bout en bout et le relier a un ticket/incident
- Contenu du prompt et de la reponse : logger systematiquement les metadonnees ; tronquer ou masquer le contenu si des donnees personnelles/sensibles sont detectees (regex, liste de mots-cles) avant d'ecrire le log
- Nombre de tokens et cout estime : a logger meme avec un LLM local, pour dimensionner l'infrastructure et detecter les derives
- Statut (succes / echec) : systematique, avec le type d'erreur le cas echeant
- Duree de conservation des logs : alignee sur la politique de retention RGPD interne (ex. 30 jours), purge automatique au-dela
