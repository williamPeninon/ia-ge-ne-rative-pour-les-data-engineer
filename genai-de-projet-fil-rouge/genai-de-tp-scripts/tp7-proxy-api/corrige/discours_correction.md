# TP7 - Discours de correction collective (fiche formateur)

Reserve au formateur. Creneau du guide : 190-210 min, « Demonstration collective, bilan » (20 min).
Le texte en *italique* est a dire a voix haute, le reste est une consigne pour vous.

| Temps | Partie | Support |
| --- | --- | --- |
| 0-2 min | Ouverture et enjeu | - |
| 2-5 min | Le schema | Tableau : un binome redessine le flux |
| 5-11 min | Les regles d'entree | `conception_proxy.md`, section 3 |
| 11-15 min | Le logging | `conception_proxy.md`, section 4 |
| 15-18 min | Demonstration en direct | Terminal, `proxy.py --simulation` |
| 18-20 min | Limites, bilan, transition | - |

Avant de commencer : ouvrez un terminal dans `corrige/` et verifiez que
`python proxy.py --simulation` tourne (les 12 cas doivent afficher `OK`).

---

## 1. Ouverture (0-2 min)

*« Ce matin on a vu le cadre : RGPD, conditions des fournisseurs, AI Act. Le TP7, c'est le moment
ou ce cadre devient du code. Je vous pose une question : si demain un collegue colle un IBAN
client dans un prompt, qu'est-ce qui l'en empeche ? »*

Laissez 2 ou 3 reponses (« la formation », « la confiance », « rien »).

*« Voila. Tant qu'on compte sur la vigilance de chacun, la reponse est : rien. Le proxy, c'est la
reponse technique. Une chaine IA n'est securisee que si elle filtre les entrees ET les sorties,
et que chaque appel reste tracable et attribuable a un usage precis. C'est la phrase du livret ;
c'est aussi la grille de correction que je vais suivre. »*

Precisez le cadre : *« Ce que je vais vous montrer est une reference pedagogique. Sur les seuils,
les listes de mots et la duree de conservation, c'est la politique de securite de la DSI qui
prevaut, toujours. Moi je vous donne les principes et une facon de les mettre en oeuvre. »*

## 2. Le schema (2-5 min)

Demandez a un binome de venir dessiner ou de dicter le flux, puis completez.

*« Attendu : Application, filtre d'entree, proxy ou gateway, API du LLM, filtre de sortie,
application. Si vous avez ca, vous avez la moitie des points. Maintenant, trois precisions que
peu d'entre vous ont mises. »*

1. *« Le proxy doit etre le seul a avoir la cle et le droit de sortie reseau vers l'API. Sinon une
   application le contourne et votre schema ne protege rien. »*
2. *« Chaque appel arrive avec une equipe et un usage. Sans eux, on ne sait pas qui consomme, on
   ne sait pas a qui facturer, on ne sait pas qui alerter. Dans ma demo c'est declaratif ; en
   production c'est deduit de l'identite authentifiee de l'application. »*
3. *« Le journal et l'alerting sont transverses : tous les blocs y ecrivent. »*

## 3. Les regles d'entree (5-11 min)

*« Trois familles de regles : la longueur, les mots interdits, les donnees sensibles. »*

**Longueur** : *« 4 000 caracteres chez moi, a vous de justifier votre chiffre. Cout, risque
d'exfiltration en masse, abus. Remarquez que je refuse, je ne tronque pas : couper un prompt
change son sens, l'utilisateur doit le savoir. »*

**Mots interdits** : *« Trois familles : injection (« ignore les instructions »), identifiants
(« mot de passe », « cle API »), marquages de confidentialite. Le piege : une simple recherche de
sous-chaine. Il faut normaliser, c'est-a-dire ignorer la casse, les accents, les espaces, et
chercher des mots entiers. Sinon « PASSWORD » passe, et « passwordless » bloque a tort. »*

**Donnees sensibles — la partie a soigner.**

*« Premiere question : bloquer ou masquer ? Regardez mon choix. L'IBAN, la carte, le numero de
securite sociale : je bloque, ca n'a aucune raison de partir chez un LLM, et le NIR a un
encadrement specifique en droit francais. L'email et le telephone : je masque. Le besoin metier
survit : « redige une relance pour [EMAIL] » reste une demande utile. C'est le principe de
minimisation du RGPD. Il n'y a pas une seule bonne reponse, il y a une reponse argumentee. »*

*« Deuxieme question, la plus importante : comment detecter un numero de carte ? »*
Laissez repondre « une regex ». Puis :

*« Une regex seule, c'est 16 chiffres. Et un numero de dossier a 16 chiffres, c'est aussi 16
chiffres. Si vous bloquez tout, les utilisateurs contournent le proxy et vous avez perdu. Ma
solution : la cle de controle. Une vraie carte respecte toujours l'algorithme de Luhn, un vrai
IBAN respecte toujours le modulo 97, un vrai NIR a une cle de deux chiffres. Un numero quelconque
les respecte presque jamais. Je supprime la majorite des faux positifs sans jamais laisser passer
une vraie donnee. »*

**Question piege** (preparez-vous, elle arrive presque toujours) :
*« Pourquoi ne pas demander au LLM de detecter les donnees personnelles ? »*
Reponse : *« Parce que pour qu'il les detecte, il faut les lui envoyer. Le filtre qui protege
l'envoi ne peut pas lui-meme envoyer la donnee. Ici on veut du deterministe, local, testable. »*

**Sortie** : *« On filtre aussi la reponse. Un modele peut restituer ou inventer un email, un
numero. Je masque, et je positionne un drapeau « revue humaine ». Et si la reponse contient un
mot de passe ou un marquage « strictement confidentiel », je la retiens. »*

## 4. Le logging (11-15 min)

*« C'est la partie ou la plupart d'entre vous ont ete trop genereux, ou trop prudents. Je veux
que vous reteniez une idee : un journal mal pense devient un second stockage de donnees
personnelles, pire que celui qu'on voulait proteger. »*

Presentez le tableau en trois colonnes, en parlant plus qu'en lisant :

- **A logger toujours** : *« horodatage, identifiant de requete, equipe, usage, modele, statut,
  motifs, duree, tokens. C'est ce qui permet de repondre a « qui a fait quoi, quand, avec quel
  resultat ». »*
- **A masquer ou pseudonymiser** : *« l'utilisateur : un hash sale. Je peux le retrouver pour un
  audit, je ne le lis pas dans le fichier. Et pour les donnees sensibles, on garde la categorie et
  le nombre — « 1 IBAN » — jamais la valeur. »*
- **A ne pas logger** : *« le contenu d'une requete ou on a detecte une donnee sensible ou un mot
  interdit. La reponse du LLM. La cle d'API. Et le message d'erreur brut du fournisseur, parce
  qu'il peut citer votre prompt. »*

*« Regle que j'applique dans le code : l'extrait du prompt n'est journalise que si le filtre n'a
rien vu. Simple a expliquer a un auditeur. »*

**Retention** : *« Trente jours en exemple, comme dans le guide : alignee sur la politique RGPD
interne, avec purge automatique. Un fichier par jour, donc purger c'est supprimer des fichiers. Une
obligation de tracabilite plus longue sur les decisions assistees par IA est possible : la duree se
fixe avec le DPO et la DSI, pas entre nous. »*

**Alerting** : *« Une alerte quand une equipe declenche trois detections en dix minutes : un
utilisateur qui reessaie d'envoyer un IBAN, ce n'est plus une erreur, c'est un signal. Une seule
alerte par fenetre, sinon on noie le SOC. L'alerte ne contient jamais de donnee. Et une deuxieme a
80 % du budget de tokens. »*

## 5. Demonstration en direct (15-18 min)

Dans l'ordre, sans improviser sur les commandes :

```bash
python proxy.py --simulation            # les 12 cas : attendu / obtenu
cat logs/audit-*.jsonl | head -3        # ce qu'on enregistre vraiment
grep -c "@" logs/audit-*.jsonl          # aucun email dans le journal : 0
python -m unittest test_proxy           # 27 tests
python proxy.py --simulation --prompt "Le virement part vers FR76 3000 6000 0112 3456 7890 189"
```

*« Regardez la colonne « attendu / obtenu » : j'ai ecrit le comportement attendu avant le code.
C'est la regle du module precedent, on definit les metriques avant de generer. »*

Montrez deux cas en particulier :

- `faux_positif_dossier` : *« 16 chiffres, et ca passe. Voila la cle de controle qui travaille. »*
- `fuite_pii_sortie` : *« Ici c'est le modele qui sort un email. Il est masque et la reponse est
  marquee pour relecture. »*

Invitez **un stagiaire a taper un prompt** avec une donnee fictive (jamais une vraie) et a deviner
le statut avant de lancer. C'est le moment le plus retenu.

Si Ollama tourne sur la VM, relancez sans `--simulation` pour montrer le cas nominal.

## 6. Limites, bilan, transition (18-20 min)

*« Pour finir, soyez honnetes sur ce que ca ne fait pas. »*

- *« Mes regex ne voient ni les noms propres ni les adresses. « Mme Durand habite rue... » passe.
  Pour ca, il faut de la reconnaissance d'entites nommees. »*
- *« Un filtre se contourne : espaces inseres, encodage, une autre langue. C'est une couche de
  defense, pas une garantie. Elle s'ajoute aux droits d'acces, a la formation et a la relecture
  humaine. »*
- *« Chaque seuil est un arbitrage entre faux positifs et faux negatifs. « mot de passe » bloque
  aussi « comment reinitialiser mon mot de passe ». Ca se mesure et ca se revoit. »*
- *« Mes quotas sont en memoire, sur un seul processus. En production : une base partagee. »*

**Bilan** : *« Si vous ne gardez que quatre choses : un point de passage unique ; bloquer ce qui ne
doit jamais sortir et masquer le reste ; ne jamais journaliser ce qu'on a protege ; et garder un
humain dans la boucle sur ce qui a ete modifie. Et la responsabilite : c'est vous, ingenieurs,
qui signez la chaine. »*

**Transition** : *« Cet apres-midi, on change de registre : on utilise l'IA pour produire de la
valeur sur des logs, du code, du SQL, de l'ingestion. Tout ce que vous avez vu ce matin s'applique
a chaque cas d'usage. »*

---

## Questions probables

| Question | Reponse courte |
| --- | --- |
| « Notre LLM est auto-heberge, pourquoi filtrer ? » | Les donnees ne quittent pas le SI, mais la minimisation, les journaux et la reutilisation des reponses restent des sujets RGPD. Et on prend la bonne habitude avant un passage a un fournisseur externe. |
| « Et si le filtre est en panne ? » | Choix a faire avec la DSI : fail-closed (on bloque tout) ou fail-open (on laisse passer en alertant). Pour des donnees bancaires, la tendance est au fail-closed. Dans ma reference, c'est le journal qui est fail-open, et c'est signale. |
| « On peut stocker les prompts pour ameliorer les prompts ? » | Seulement ceux sans donnee sensible, tronques, avec une retention bornee, et avec l'accord du DPO. |
| « Pourquoi 30 jours ? » | C'est l'exemple du guide. La valeur reelle vient de la politique interne et des obligations de tracabilite. |
| « L'AI Act, ca change quoi ici ? » | Selon le niveau de risque du cas d'usage : obligations de transparence, de supervision humaine et de tracabilite. Le proxy y contribue, il ne suffit pas. Renvoyez vers la DSI/conformite pour le classement de risque. |
| « Pourquoi pas une bibliotheque toute faite ? » | Si, en production (par ex. Presidio pour les entites nommees). Ici l'objectif est de comprendre ce qu'elle fait. |

## Erreurs frequentes a relever dans les copies

- Schema sans filtre de sortie.
- Tout bloquer ou tout masquer sans argumenter.
- Logger le prompt complet « pour pouvoir debugger ».
- Retention absente, ou « pour toujours ».
- Alerte sur chaque detection (bruit) ou aucune alerte.
- Cle d'API dans le code ou dans l'image.

## Avant la session

- [ ] `python proxy.py --simulation` : 12 cas `OK`
- [ ] `python -m unittest test_proxy` : 27 tests `OK`
- [ ] Supprimer `corrige/logs/` apres la demo (ignore par Git, mais inutile a distribuer)
- [ ] Ne distribuer `corrige/` qu'apres la demonstration collective
