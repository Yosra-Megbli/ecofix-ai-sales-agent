# Follow-up Message Templates

Templates utilisés par `backend/services/follow_up_sender.py`.

Variables disponibles : `{prenom}`, `{nom}`, `{fournisseur}`.
Si une variable est absente du lead, elle est remplacée par une valeur neutre.

Format des sections : `## CLE` suivi du texte du message.
Ne pas modifier les noms de clés (HOT_1, WARM_1, etc.) — ils sont référencés par le code.

---

## HOT_1
Bonjour {prenom},

je reviens vers vous concernant votre demande Ecofix Gas & Power.

Vous étiez sur le point de finaliser votre dossier. Souhaitez-vous que nous poursuivions ensemble les prochaines étapes ?

Je suis disponible pour répondre à toutes vos questions. 😊

---

## WARM_1
Bonjour {prenom},

je voulais simplement reprendre contact suite à notre échange concernant Ecofix Gas & Power.

Avez-vous eu le temps de réfléchir à votre situation énergétique ? Nous proposons des offres très compétitives en Wallonie et en Flandre.

N'hésitez pas à me poser vos questions, je suis là pour vous aider.

---

## WARM_2
Bonjour {prenom},

je reviens une dernière fois avec une information utile : saviez-vous que chez Ecofix, chaque ami parrainé vous rapporte 5 € de réduction par mois sur votre facture ?

Si vous avez des questions sur nos offres Flexy ou Motion, je suis disponible pour en discuter.

---

## COLD_1
Bonjour {prenom},

nous avons échangé récemment au sujet de votre contrat d'énergie avec {fournisseur}.

Si vous souhaitez comparer votre offre actuelle avec Ecofix Gas & Power, je reste disponible pour vous accompagner.

---

## COLD_2
Bonjour {prenom},

c'est notre dernier message de notre part concernant Ecofix Gas & Power.

Si vous changez d'avis et souhaitez comparer votre offre énergétique, n'hésitez pas à nous recontacter. Bonne continuation ! 👋
