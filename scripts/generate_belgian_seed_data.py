import csv
import random

# Common Belgian first and last names
first_names = ["Jean", "Pierre", "Yasmine", "Anissa", "Marc", "Sophie", "Lucas", "Charlotte", "Michel", "Sarah", "Thomas", "Emma"]
last_names = ["Dupont", "Benali", "Peeters", "Janssens", "Lambert", "Maes", "Mertens", "Claes", "Gérard", "Barthélemy"]

# Eligible Belgian cities (Wallonia / Flanders) and ineligible (Brussels)
eligible_cities = [
    ("Namur", "Rue de l'Ange 5"),
    ("Liège", "Rue de la Cathédrale 12"),
    ("Charleroi", "Rue de la Montagne 45"),
    ("Mons", "Grand Place 1"),
    ("Gand", "Veldstraat 10"),
    ("Anvers", "Meir 21"),
    ("Bruges", "Steenstraat 8")
]
ineligible_cities = [
    ("Bruxelles", "Rue Royale 10"),
    ("Ixelles", "Chaussée de Wavre 150"),
    ("Uccle", "Avenue Brugmann 300")
]

suppliers = ["Engie", "Luminus", "TotalEnergies", "Eneco", "Mega"]

def generate_ean():
    # Belgian EAN starts with 54 and has 18 digits
    digits = [str(random.randint(0, 9)) for _ in range(16)]
    return "54" + "".join(digits)

def generate_phone():
    # Belgian mobile starts with +324
    digits = [str(random.randint(0, 9)) for _ in range(8)]
    return "+324" + "".join(digits)

def generate_leads(count=100):
    leads = []
    for i in range(count):
        # 70% eligible, 30% ineligible
        is_eligible = random.random() < 0.70
        
        prenom = random.choice(first_names)
        nom = random.choice(last_names)
        email = f"{prenom.lower()}.{nom.lower()}{i}@example.com"
        phone = generate_phone()
        
        if is_eligible:
            city, address = random.choice(eligible_cities)
            ean = generate_ean()
        else:
            # Can be Brussels, underage, or invalid EAN
            reason = random.choice(["brussels", "underage", "invalid_ean"])
            if reason == "brussels":
                city, address = random.choice(ineligible_cities)
                ean = generate_ean()
            elif reason == "underage":
                city, address = random.choice(eligible_cities)
                ean = generate_ean()
            else:
                city, address = random.choice(eligible_cities)
                # 13 digits EAN (invalid format)
                ean = "".join([str(random.randint(0, 9)) for _ in range(13)])
                
        supplier = random.choice(suppliers)
        
        leads.append({
            "Nom": nom,
            "Prénom": prenom,
            "Email": email,
            "Téléphone": phone,
            "Adresse": address,
            "Ville": city,
            "Code EAN": ean,
            "Fournisseur actuel": supplier,
            "Statut": "New"
        })
    return leads

def main():
    leads = generate_leads(100)
    with open("leads_belgium_100.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Nom", "Prénom", "Email", "Téléphone", "Adresse", "Ville", "Code EAN", "Fournisseur actuel", "Statut"])
        writer.writeheader()
        writer.writerows(leads)
    print("Generated 100 Belgian dummy leads in leads_belgium_100.csv successfully!")

if __name__ == "__main__":
    main()
