# Base de connaissances Ecofix Gas & Power — pour System Prompt + RAG

Source : site officiel https://www.ecofixgp.be/fr/ (consulté le 10/07/2026)

## Identité de l'entreprise
- Nom complet : Ecofix Gas & Power
- Siège : Kunstlaan 56, 1000 Bruxelles, Belgique
- N° d'entreprise : BE.1011.812.443
- Contact : hello@ecofixgp.be
- Fondateur/PDG : Yassine Hasnaoui
- Origine : équipe expérimentée dans la vente de contrats d'énergie et
  l'installation de panneaux solaires (Ecofix Solutions), certains membres
  viennent de Lampiris (aujourd'hui TotalEnergies)
- Zone de service : Flandre et Wallonie (Belgique)
- Positionnement prix : ni le plus cher, ni le moins cher — un bon
  compromis transparent, confirmé compétitif dans des comparatifs
  indépendants (souvent 1ère-2e place en Wallonie/Flandre)

## Slogan et ton de marque
"De l'énergie futée pour tous." / "Faites plus avec la même énergie."
Ton : direct, simple, sans jargon, transparence assumée ("énergie sans
blabla, tellement transparente que votre facture la comprend enfin aussi").
Registre tutoiement/vouvoiement mixte selon les pages — pour l'agent,
rester au vouvoiement professionnel par défaut.

## Offres commerciales (2 formules, chacune en électricité et gaz)

### Ecofix Flexy — tarif variable classique
- Prix réajusté chaque mois selon le marché
- Frais de plateforme mensuels : 5,99 €
- Acompte mensuel optionnel
- Paiement par domiciliation ou virement
- Service client par téléphone et en ligne
- Factures digitales
- Disponible en Flandre et Wallonie
- Existe aussi en version "Flexy Online" (100% digitale, sans service
  téléphonique dédié, généralement légèrement moins chère)

### Ecofix Motion — tarif dynamique
- Prix aligné sur le marché en temps réel, mis à jour toutes les 15 minutes
- Permet de déplacer sa consommation vers les heures les moins chères
  (ex : recharge véhicule électrique la nuit)
- Mêmes conditions que Flexy (5,99 €/mois, acompte optionnel,
  domiciliation/virement, service client tél + en ligne)
- Existe aussi en version "Motion Online"

## Application mobile Ecofix
- Suivi des prix du marché en direct, par quart d'heure
- Suivi de sa consommation et de ses pics de consommation en temps réel
- Ajustement de l'acompte mensuel en un clic
- Visualisation et paiement des factures directement dans l'app
- Programme de parrainage intégré (suivi des amis parrainés et économies
  réalisées)
- Disponible sur iOS et Android

## Programme de parrainage "Friends with Benefits"
- 5 € de réduction par mois, par ami parrainé qui devient et reste client
- Réduction récurrente (pas une promo unique), cumulable
- Exemple concret : 2 amis parrainés = environ 120 €/an d'économies
- Ne s'applique généralement pas aux formules 100% en ligne (Flexy
  Online / Motion Online) — à vérifier au cas par cas si le prospect
  demande une précision, ne pas garantir sans certitude

## Arguments de différenciation à mettre en avant
1. Transparence totale : pas de coûts cachés, structure de prix claire
   dans l'application
2. Contrôle en temps réel : contrairement à d'autres fournisseurs où
   "on découvre sa consommation au décompte annuel", Ecofix montre tout
   en direct
3. Flexibilité : possibilité de switcher entre offre variable et
   dynamique selon le profil du client
4. Économies sociales : le parrainage transforme le bouche-à-oreille en
   économies récurrentes réelles

## FAQ type (à utiliser telles quelles ou reformulées par l'agent)

**Qu'est-ce qui différencie Ecofix des autres fournisseurs ?**
La transparence des prix (visibles en direct dans l'app), l'absence de
frais cachés, et le programme de parrainage qui fait baisser la facture
mois après mois.

**Qu'est-ce qu'un tarif dynamique ?**
Un tarif qui suit le prix réel du marché de l'énergie, réactualisé toutes
les 15 minutes. Idéal pour les clients qui peuvent adapter leur
consommation (ex : recharge de véhicule électrique, électroménager) aux
heures les moins chères.

**Quelle formule choisir : Flexy ou Motion ?**
- Flexy (variable) : pour un client qui veut de la simplicité, un prix
  révisé une fois par mois, sans avoir à surveiller le marché.
- Motion (dynamique) : pour un client actif, à l'aise avec l'idée de
  suivre les prix en temps réel via l'app pour optimiser sa consommation.

**Comment passer chez Ecofix ?**
Le changement de fournisseur se fait simplement en ligne via le portail
client (portal.ecofixgp.be), généralement sans coupure de service.

**Puis-je inviter des proches ?**
Oui, via le programme "Friends with Benefits" dans l'application —
5 €/mois de réduction par ami parrainé actif.

---

## Instructions pour l'intégration

**Dans le system prompt de l'agent (backend/agent/prompts.py) :**
Ajouter un résumé condensé de l'identité, du ton de marque, des 2 offres
(Flexy/Motion) et de leur différence, plus le programme de parrainage.
L'agent doit pouvoir répondre "quel fournisseur êtes-vous / que proposez-
vous" avec ces vraies infos, au lieu de rester générique sur "l'énergie".

**Dans le RAG (Phase 4, à venir) :**
Découper ce document en chunks par section (Offres, Application, FAQ,
Parrainage) pour une recherche sémantique plus fine, chaque FAQ comme un
chunk indépendant.

**Point d'honnêteté important :** ce contenu vient du site belge
ecofixgp.be. Si le vrai client (celui que tu dois convaincre) a des
tarifs, une zone de couverture ou des offres différentes de ce qui est
décrit ici, il faut ajuster ces chiffres avec les vraies infos qu'il te
donnera — ne présente jamais un chiffre non confirmé comme définitif
face au client final.
