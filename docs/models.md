# Data Models — Airtable schema (Phase 1)

This document defines the Airtable tables and fields for the AI Sales Agent.

1) Leads (table: `Leads`)
- Lead ID: string (unique, system or generated)
- Nom: string
- Prénom: string
- Téléphone: string
- Email: string
- Adresse: string
- Ville: string
- Code EAN: string
- Fournisseur actuel: string
- Statut: single select (New, Contacted, Replied, Qualified, Appointment, Contract Sent, Sold, Rejected)
- Score IA: number
- Dernier contact: datetime
- Prochaine action: string

2) Conversations (table: `Conversations`)
- Lead: link to Leads
- Date: datetime
- Client Message: long text
- AI Reply: long text
- Detected Intent: single select (Inquiry, Complaint, Pricing, Interested, Other)
- Objection: long text
- AI Summary: long text

3) Campaigns (table: `Campaigns`)
- Name: string
- Lead Count: number
- Start Date: date
- End Date: date
- Status: single select (Planned, Running, Paused, Completed)

Validation & Dedupe rules
- Primary dedupe keys: Email, Phone, EAN Code. If any match an existing record, treat as duplicate.
- Basic validation: Email must match regex, Phone must be digits (with optional +), required fields: First/Last name, Email or Phone.

Usage
- These field names are used by the Airtable client in `backend/airtable_client.py` and CSV import script `scripts/import_csv.py`.
