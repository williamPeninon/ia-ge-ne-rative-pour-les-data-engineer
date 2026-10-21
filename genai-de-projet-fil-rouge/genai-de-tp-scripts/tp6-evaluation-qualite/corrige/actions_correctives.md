# Metriques et actions correctives (corrige)

## Les 3 metriques definies

Principe : on les definit avant de generer, on les calcule en code (pas par un LLM), et on
fixe un seuil d'acceptation du jeu.

| Metrique | Definition (comment on la calcule) | Seuil d'acceptation |
| --- | --- | --- |
| Conformite de schema | Part des enregistrements valides au JSON Schema (champs obligatoires, types, pattern du matricule, dates reelles AAAA-MM-JJ) | 100 % |
| Plausibilite des valeurs | Part des enregistrements dont les valeurs sont credibles : noms/prenoms composes de lettres, champs texte non vides, date_naissance < date_entree, age a l'embauche entre 16 et 70 ans, date d'entree passee et posterieure a 1980 | >= 95 % |
| Absence de doublons | Part des enregistrements sans doublon : matricule unique, et personne unique (nom + prenom + date de naissance) | 100 % |

## Anomalies detectees (jeu_secours.json) et action corrective

| Enregistrement | Anomalie | Comment la detecter | Action corrective |
| --- | --- | --- | --- |
| M10006 | Prenom incoherent `Xyz123` | Regex lettres / tiret / apostrophe sur nom et prenom | Regle de validation + regeneration ciblee de l'enregistrement |
| M10019 | Nom incoherent `###` | Idem | Idem |
| M10007 | date_naissance (2001) posterieure a date_entree (1999) | Comparaison des deux dates | Regle metier + regeneration ciblee en rappelant la contrainte dans le prompt |
| M10012 | Age a l'embauche de 12 ans | Plage 16-70 ans sur (date_entree - date_naissance) | Regle de plage + regeneration ciblee |
| M10013 | date_entree dans le futur (2045) | Plage de dates : ni futur, ni avant 1980 | Regle de plage + regeneration ciblee |
| M10003 (2e occurrence) | Matricule duplique | Comptage des matricules (unicite non exprimable dans le JSON Schema) | Garder la 1re occurrence, regenerer la 2e avec un matricule libre ; unicite controlee par le code |
| M10014 | Personne en double (meme identite que M10001) sous un autre matricule | Cle nom + prenom + date de naissance normalisee (casse, espaces) | Rejet du doublon (filtre de rejet) ; augmenter la diversite (temperature, noms tires d'une liste) |
| M1011 | Matricule `M1011` : 4 chiffres au lieu de 5 | Pattern `^M[0-9]{5}$` du schema | Regle regex avant integration + regeneration ciblee |
| M10016 | Date de naissance `1975-13-40` (mois 13) | `format: date` verifie avec FormatChecker | Validation de format + regeneration ciblee |
| M10015 | Poste vide | Texte non vide exige | Champ obligatoire non vide dans le prompt + regeneration ciblee |

Resultat attendu sur `jeu_secours.json` : 18 enregistrements dont 10 suspects. Seuls 8 sont
integrables tels quels.

## Que fait-on d'un enregistrement fautif avant integration au jeu final ?

Un enregistrement qui echoue n'entre jamais tel quel dans le jeu final. Chaine appliquee :

1. Calcul des 3 metriques sur la sortie brute du LLM
2. Filtre de rejet automatique : les enregistrements en anomalie sont ecartes
   (`dataset_rejets.json`, avec la liste des regles violees)
3. Regeneration ciblee (option `--regenerer`) : on redemande uniquement l'enregistrement
   fautif, en donnant au LLM la raison du rejet, avec un nombre d'essais borne
4. Le candidat regenere repasse les memes controles avant d'etre integre ; apres
   plusieurs echecs, il reste rejete (jamais force dans le jeu)

## Points de vigilance

- L'unicite (matricule) et les relations entre champs (dates, age) ne se garantissent pas
  dans le prompt : le LLM les viole regulierement. Elles se verifient en code.
- Un `format: date` n'est verifie par jsonschema que si l'on passe un `FormatChecker`. Sans
  lui, `1975-13-40` est declare conforme.
- Le schema du TP5 n'a pas de champ salaire : si on en ajoute un, ajouter une regle de plage
  (ni negatif, ni aberrant) dans la plausibilite.

## Pour aller plus loin (hors TP)

- LLM-as-a-judge : un second appel LLM note le realisme des postes/departements
- Recoupement avec un referentiel (liste officielle des departements et des postes)
- Plausibilite statistique : distribution des ages et anciennetes comparee a une cible
