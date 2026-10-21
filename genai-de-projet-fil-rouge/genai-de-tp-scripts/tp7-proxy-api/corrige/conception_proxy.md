# Proxy API avec filtrage des entrees - conception (corrige)

Reserve au formateur. Reference executable : `proxy.py` (tests : `test_proxy.py`).
Rappel : les valeurs ci-dessous (seuils, listes, retention) sont des exemples pedagogiques ;
la politique de securite interne de la DSI prevaut toujours.

## 1. Schema d'architecture

```
                         +------------------ Journal d'audit (JSONL, 1 fichier/jour) ---> Purge (retention)
                         |                              ^         ^         ^
                         |                              |         |         |
  Application --> [1] Filtre d'entree --> [2] Proxy / Gateway --> API du LLM
   (equipe,           longueur max           attribution                |
    usage,            mots interdits         quota de tokens            v
    prompt)           PII : bloquer/masquer  plafond de reponse   [3] Filtre de sortie --> Application
                                             timeout                  PII masquees                |
                                                                      mots interdits              |
                                                                      revue humaine <-------------+
                                  Alerting : detections repetees, budget de tokens
```

| Bloc | Role | Ce qu'il decide |
| --- | --- | --- |
| Filtre d'entree | Controler ce qui sort de l'entreprise | Laisser passer, masquer ou bloquer |
| Proxy / Gateway | Point de passage unique vers l'API | Attribuer l'appel, appliquer le quota, appeler le LLM, journaliser |
| Filtre de sortie | Controler ce qui revient | Renvoyer, masquer, retenir (et signaler pour revue humaine) |
| Journal d'audit | Rendre chaque appel tracable | Quoi enregistrer, quoi ne jamais enregistrer |

Le proxy est le seul composant autorise a joindre l'API du LLM (filtrage des flux sortants au
niveau reseau) : sans cela, une application peut le contourner et le schema ne protege rien.

## 2. Pseudo-code

```
completer(messages, equipe, usage, utilisateur):
    id = nouvel_uuid()
    si equipe ou usage manquant ou messages invalides:  -> journaliser + REFUSER (requete_invalide)

    # 1. Filtre d'entree
    si longueur_totale(messages) > LONGUEUR_MAX:         -> journaliser + REFUSER (sans tronquer)
    pour chaque message:
        donnees = detecter_donnees_sensibles(message)     # regex + cle de controle (Luhn, mod 97, NIR)
        si une donnee est de niveau "bloquer":            bloquer = vrai
        si un mot interdit est present:                   bloquer = vrai
        message = masquer(message, donnees)               # [EMAIL], [TELEPHONE] ...
    si bloquer:                                           -> journaliser (categories seulement) + REFUSER

    # 2. Gateway
    si quota_equipe_depasse(equipe):                      -> journaliser + REFUSER (quota_depasse)
    reponse = appeler_llm(messages_masques, max_tokens=PLAFOND, timeout=T)   # erreur: type seulement
    comptabiliser_tokens(equipe, reponse.usage)

    # 3. Filtre de sortie
    si mot_interdit_critique(reponse):                    -> journaliser + RETENIR (revue humaine)
    reponse = masquer(reponse, detecter_donnees_sensibles(reponse))

    journaliser(metadonnees)
    si incident_de_securite: alerter_si_recurrent(equipe)
    renvoyer reponse
```

## 3. Regles de filtrage

### Entrees

| Regle | Detection | Decision | Justification |
| --- | --- | --- | --- |
| Attribution | `equipe` et `usage` renseignes | Refuser sinon | Chaque appel doit etre attribuable a un usage precis (cout, audit) |
| Longueur maximale | 4 000 caracteres au total (~1 000 tokens) | Refuser (pas de troncature) | Maitrise du cout, limite l'exfiltration en masse ; tronquer changerait le sens |
| IBAN | Motif + controle modulo 97 | Bloquer | Donnee bancaire : n'a aucune raison de partir vers un LLM |
| Carte bancaire | 13-19 chiffres + controle de Luhn | Bloquer | Donnee PCI-DSS |
| N° de securite sociale | Motif + cle de controle (2 chiffres) | Bloquer | Donnee a haut risque (RGPD, art. 87) |
| Email, telephone | Regex | Masquer (`[EMAIL]`, `[TELEPHONE]`) puis envoyer | Le besoin metier survit au masquage ; principe de minimisation |
| Mots interdits - injection | « ignore les instructions », « affiche ton prompt systeme »... | Bloquer | Tentative de detournement du modele |
| Mots interdits - identifiants | « mot de passe », « cle api », « token d'acces »... | Bloquer | Un secret ne doit jamais etre colle dans un prompt |
| Mots interdits - classification | « strictement confidentiel », « diffusion restreinte » | Bloquer | Respect du marquage des documents |
| Quota | Tokens consommes par equipe sur la journee | Refuser au-dela du plafond | Budget et continuite de service pour les autres equipes |

Choix techniques a justifier :

- **Cle de controle plutot que regex seule.** Un numero de dossier a 16 chiffres n'est pas une
  carte. Les vraies donnees respectent toujours leur cle de controle ; les numeros quelconques
  presque jamais. On supprime la plupart des faux positifs sans laisser passer de vraie donnee.
- **Bloquer vs masquer.** On bloque ce qui ne doit jamais sortir, on masque ce dont le besoin
  metier survit au masquage. La categorie inconnue est traitee comme « bloquer » (prudence).
- **Comparaison normalisee des mots-cles** : casse, accents, apostrophes et espaces ignores,
  mots entiers uniquement (`passwordless` ne declenche pas `password`).

### Sorties

| Regle | Decision |
| --- | --- |
| Donnee sensible dans la reponse (le modele peut en inventer ou en restituer) | Masquer + signaler `revue_humaine` |
| Mot interdit critique (identifiants, classification) | Retenir la reponse, `bloque_sortie` + revue humaine |
| Reponse trop longue | Tronquer a 8 000 caracteres + signaler |

### Limites a faire dire aux stagiaires

- Les regex ne couvrent ni les noms propres, ni les adresses postales, ni le texte libre
  (« Mme Durand habite rue... »). Pour cela : reconnaissance d'entites nommees (ex. Presidio).
- Un filtre se contourne (espaces insere, encodage, homoglyphes, autre langue) : c'est une
  couche de defense, jamais une garantie. Elle s'ajoute a la formation des utilisateurs, aux
  droits d'acces et a la relecture humaine.
- Tout seuil est un arbitrage faux positifs / faux negatifs (« mot de passe » bloque aussi
  « comment reinitialiser mon mot de passe ? »). Il se mesure sur des cas reels et se revoit.

## 4. Niveau de logging

| Element | Action | Justification |
| --- | --- | --- |
| Horodatage UTC, `request_id`, equipe, usage, modele, version de la politique | **Logger toujours** | Tracabilite, correlation avec un incident, savoir quelle regle a decide |
| Statut (`ok`, `ok_masque`, `bloque_entree`, `bloque_sortie`, `quota_depasse`, `erreur_llm`) et motifs | **Logger toujours** | Audit, tableau de bord, detection de derive |
| Duree, tokens (prompt / reponse / total), longueurs | **Logger toujours** | Cout et dimensionnement |
| Identifiant utilisateur | **Pseudonymiser** (hash sale) | Retrouvable pour un audit, non lisible dans le fichier |
| Categories et nombre de donnees sensibles detectees | **Logger** | Mesure du risque, alerting ; jamais les valeurs |
| Hash du prompt (apres masquage) | **Logger** | Detecter les repetitions et prouver le contenu sans le stocker |
| Extrait du prompt (200 premiers caracteres) | **Logger seulement si rien de sensible n'a ete detecte** | Aide au diagnostic, sans risque |
| Contenu d'une requete ou une donnee sensible / un mot interdit a ete detecte | **Ne pas logger** | Le log deviendrait un second stockage de donnees personnelles (voire de secrets) |
| Contenu de la reponse du LLM | **Ne pas logger** (longueur seulement) | Peut contenir des donnees ; reconstituable via le hash et la requete |
| Cle d'API, secrets, en-tetes d'autorisation | **Jamais** | Un log est lu par plus de monde que le coffre-fort |
| Message d'erreur brut du fournisseur | **Ne pas logger** (type d'exception seulement) | Peut citer le prompt |

Retention et protection des journaux :

- **30 jours** (exemple) alignes sur la politique RGPD interne, avec **purge automatique**
  (un fichier par jour : on supprime les fichiers trop anciens, sans jamais reecrire un journal).
  Une obligation de tracabilite plus longue sur les decisions assistees par IA est possible :
  duree a fixer avec le DPO et la DSI, pas par l'equipe technique.
- Fichiers en lecture restreinte (droits 0600, acces nominatif), chiffrement au repos au niveau
  du volume, journaux hors du depot Git (`logs/` ignore).

Alerting :

| Declencheur | Seuil d'exemple | Destinataire | Contenu de l'alerte |
| --- | --- | --- | --- |
| Detections sensibles repetees (donnee sensible ou mot interdit) | 3 en 10 min pour une meme equipe, une alerte par fenetre | RSSI / SOC + responsable d'equipe | Equipe, nombre, fenetre - jamais de donnee |
| Budget de tokens | 80 % du plafond journalier | Responsable d'equipe | Equipe, ratio consomme |
| (En production) taux d'erreurs LLM, latence | A definir avec l'exploitation | Exploitation | Taux, periode |

## 5. Securite de l'ensemble

- **Secrets** : cle d'API dans une variable d'environnement ou un coffre-fort, jamais dans le
  code, l'image Docker ou les logs ; une cle par equipe ou projet (attribution, revocation,
  rotation sans impact global).
- **Identite** : en production, `equipe` et `usage` sont deduits de l'identite authentifiee de
  l'application appelante (jeton, mTLS) et non declares librement par l'appelant, comme dans la demo.
- **Transport** : TLS entre l'application, le proxy et l'API.
- **Humain dans la boucle** : le champ `revue_humaine` signale les reponses alterees par le
  filtre ; plus generalement, toute decision assistee par IA est relue et tracee avant usage.
- **LLM auto-heberge (Ollama)** : les donnees ne quittent pas le SI, mais le filtrage reste
  utile (minimisation, journaux, reutilisation des reponses). Avec un fournisseur externe, les
  conditions d'utilisation (retention, entrainement sur les donnees) et les transferts hors UE
  sont a verifier avant tout envoi.

## 6. Ce que la reference n'implemente pas

- Quotas et compteurs en memoire, sur un seul processus (en production : Redis ou base de donnees partagee).
- Pas d'authentification de l'appelant ni de streaming.
- Si l'ecriture du journal echoue, le service continue (erreur visible) : a arbitrer avec la DSI
  entre disponibilite et obligation d'audit (blocage possible).
- Detection par regex : pas de reconnaissance de noms propres ni d'adresses.
- Chiffrement des journaux delegue a l'infrastructure.

## 7. Grille de correction (a comparer aux productions des stagiaires)

- [ ] Schema complet : Application -> Filtre d'entree -> Proxy/Gateway -> API LLM -> Filtre de sortie -> Application
- [ ] Filtre d'entree : donnees personnelles/sensibles detectees avant envoi, longueur maximale, liste de mots interdits
- [ ] Distinction bloquer / masquer argumentee
- [ ] Logging : metadonnees et statut de chaque appel systematiquement journalises
- [ ] Contenu des prompts contenant des donnees personnelles masque ou non journalise
- [ ] Retention alignee sur la politique RGPD interne (ex. 30 jours), purge automatique
- [ ] Alerting en cas de detection repetee de donnees sensibles
- [ ] Bonus : filtre de sortie, quota par equipe, gestion des secrets, relecture humaine, limites des regex
