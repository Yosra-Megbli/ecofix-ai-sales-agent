"""CSV import script for Airtable Leads."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import re
from typing import Dict

from backend.airtable_client import AirtableClient

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_row(row: Dict[str, str]) -> bool:
    if not (row.get("Nom") or row.get("Prénom")):
        return False
    if not (row.get("Email") or row.get("Téléphone")):
        return False
    if row.get("Email") and not EMAIL_RE.match(row.get("Email")):
        return False
    return True


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^0-9+]", "", phone or "")


def import_csv(path: str, airtable_table: str = "Leads"):
    client = AirtableClient()
    created = 0
    skipped = 0
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not validate_row(row):
                print("Skipping invalid row:", row)
                skipped += 1
                continue

            existing = None
            if row.get("Email"):
                existing = client.find_by_field(airtable_table, "Email", row.get("Email"))
            if not existing and row.get("Téléphone"):
                existing = client.find_by_field(airtable_table, "Téléphone", normalize_phone(row.get("Téléphone")))
            if not existing and row.get("Code EAN"):
                existing = client.find_by_field(airtable_table, "Code EAN", row.get("Code EAN"))

            if existing:
                print("Duplicate found, skipping:", row.get("Email") or row.get("Téléphone"))
                skipped += 1
                continue

            fields = {
                "Nom": row.get("Nom"),
                "Prénom": row.get("Prénom"),
                "Email": row.get("Email"),
                "Téléphone": normalize_phone(row.get("Téléphone")),
                "Adresse": row.get("Adresse"),
                "Ville": row.get("Ville"),
                "Code EAN": row.get("Code EAN"),
                "Fournisseur actuel": row.get("Fournisseur actuel"),
                "Statut": "New",
            }
            client.create_record(airtable_table, fields)
            created += 1

    print(f"Import finished. Created={created}, Skipped={skipped}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_csv.py path/to/leads.csv")
        sys.exit(1)
    import_csv(sys.argv[1])
