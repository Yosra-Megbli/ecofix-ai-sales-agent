# Règles du Moteur de Qualification et d'Éligibilité

Pour qu'un Lead soit considéré comme valide et éligible, l'agent ou le code backend doit vérifier :

## 1. Données obligatoires à collecter
Chaque lead doit obligatoirement renseigner :
- **Nom** et **Prénom**
- **Téléphone** (format valide)
- **Email** (format valide)
- **Adresse** et **Ville**
- **Date de naissance**
- **Code EAN** (18 chiffres)
- **Volonté de changer de fournisseur** (doit être explicite ou implicite positive)

## 2. Critères stricts d'Éligibilité (Qualification)
Un lead est marqué comme **Éligible** (Statut: `Qualified`) si :
1. Sa ville ou son adresse est située en **Wallonie** ou en **Flandre** (Belgique). Si l'adresse mentionne Bruxelles (Bruxelles, Ixelles, Uccle, Evere, Anderlecht, etc.), le prospect n'est pas éligible.
2. Sa date de naissance montre qu'il est majeur (au moins **18 ans**).
3. Il exprime son désir de changer de fournisseur d'énergie.
4. Son code EAN à 18 chiffres commence bien par **54** (compteurs d'électricité/gaz belges).

Si l'un de ces critères n'est pas rempli, le prospect est classé comme **Inéligible** (Statut: `Rejected`).
