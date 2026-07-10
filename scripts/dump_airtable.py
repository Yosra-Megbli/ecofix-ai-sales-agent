from backend.airtable_client import AirtableClient

def main():
    client = AirtableClient()
    try:
        data = client.list_records("Leads")
        records = data.get("records", [])
        print(f"Total records in Leads: {len(records)}\n")
        print("List of Leads:")
        for idx, rec in enumerate(records):
            fields = rec.get("fields", {})
            nom = fields.get("Nom", "N/A")
            prenom = fields.get("Prenom", "N/A")
            email = fields.get("Email", "N/A")
            statut = fields.get("Statut", "New")
            print(f"{idx+1}. {prenom} {nom} | {email} | Statut: {statut}")
            
        print("\n" + "="*40 + "\n")
        
        conv_data = client.list_records("Conversations")
        conv_records = conv_data.get("records", [])
        print(f"Total records in Conversations: {len(conv_records)}")
        
    except Exception as e:
        print("Error connecting to Airtable:", e)

if __name__ == "__main__":
    main()
