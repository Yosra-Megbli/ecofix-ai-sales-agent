"""Routes for Lead management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import re
from backend.airtable_client import AirtableClient
from backend.schemas import LeadCreate, LeadRead, LeadUpdate

router = APIRouter()
client = AirtableClient()
AIRTABLE_TABLE = "Leads"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_phone(phone: str) -> str:
    """Normalize phone number by removing non-digit/+ characters."""
    return re.sub(r"[^0-9+]", "", phone or "")


def _airtable_record_to_lead_read(record: dict) -> LeadRead:
    """Convert Airtable record to LeadRead schema."""
    fields = record.get("fields", {})
    
    # Map Airtable fields (French names) to Pydantic model
    # Using alias names since populate_by_name=True
    return LeadRead(**{
        "lead_id": record.get("id"),
        "Nom": fields.get("Nom"),
        "Prénom": fields.get("Prénom"),
        "Téléphone": fields.get("Téléphone"),
        "Email": fields.get("Email"),
        "Adresse": fields.get("Adresse"),
        "Ville": fields.get("Ville"),
        "Code EAN": fields.get("Code EAN"),
        "Fournisseur actuel": fields.get("Fournisseur actuel"),
        "Statut": fields.get("Statut", "New"),
        "Score IA": fields.get("Score IA"),
        "Dernier contact": fields.get("Dernier contact"),
        "Prochaine action": fields.get("Prochaine action"),
    })


@router.get("", response_model=List[LeadRead])
async def list_leads(
    statut: Optional[str] = Query(None, description="Filter by lead status"),
    email: Optional[str] = Query(None, description="Filter by email")
):
    """
    Get all leads from Airtable.
    
    Optional query parameters:
    - statut: Filter by lead status (e.g., "New", "Contacted", "Qualified")
    - email: Filter by email address
    
    Returns:
        List of leads with all fields
    """
    try:
        params = {}
        
        # Build filter formula if filters provided
        if statut or email:
            filters = []
            if statut:
                filters.append(f'{{Statut}} = "{statut}"')
            if email:
                filters.append(f'{{Email}} = "{email}"')
            
            if filters:
                # Combine filters with AND
                filter_formula = "AND(" + ", ".join(filters) + ")"
                params["filterByFormula"] = filter_formula
        
        response = client.list_records(AIRTABLE_TABLE, params=params if params else None)
        records = response.get("records", [])
        
        return [_airtable_record_to_lead_read(record) for record in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leads: {str(e)}")


@router.post("", response_model=LeadRead, status_code=201)
async def create_lead(lead: LeadCreate):
    """
    Create a new lead in Airtable.
    
    Handles deduplication: if lead matches existing Email, Phone, or EAN, raises 409 Conflict.
    
    Args:
        lead: Lead data to create
        
    Returns:
        Created lead with Airtable ID (raise 409 if duplicate detected)
    """
    try:
        # Get the lead data as dict for validation
        lead_data = lead.model_dump(by_alias=True, exclude_none=True)
        
        # Check for duplicates: Email, Phone, EAN
        existing = None
        
        if lead_data.get("Email"):
            existing = client.find_by_field(AIRTABLE_TABLE, "Email", lead_data.get("Email"))
        
        if not existing and lead_data.get("Téléphone"):
            existing = client.find_by_field(
                AIRTABLE_TABLE,
                "Téléphone",
                normalize_phone(lead_data.get("Téléphone"))
            )
        
        if not existing and lead_data.get("Code EAN"):
            existing = client.find_by_field(AIRTABLE_TABLE, "Code EAN", lead_data.get("Code EAN"))
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate lead detected: Email={lead_data.get('Email')} or Phone={lead_data.get('Téléphone')} or EAN={lead_data.get('Code EAN')} already exists"
            )
        
        # Create the lead
        response = client.create_record(AIRTABLE_TABLE, lead_data)
        return _airtable_record_to_lead_read(response)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating lead: {str(e)}")


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: str):
    """
    Retrieve a specific lead by ID.
    
    Args:
        lead_id: Airtable record ID
        
    Returns:
        Lead details or 404 if not found
    """
    try:
        response = client.get_record(AIRTABLE_TABLE, lead_id)
        return _airtable_record_to_lead_read(response)
    except Exception as e:
        if "404" in str(e) or "NOT_FOUND" in str(e):
            raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
        raise HTTPException(status_code=500, detail=f"Error fetching lead: {str(e)}")


@router.put("/{lead_id}", response_model=LeadRead)
async def update_lead(lead_id: str, lead: LeadUpdate):
    """
    Update an existing lead.
    
    Args:
        lead_id: Airtable record ID
        lead: Updated lead data (all fields optional)
        
    Returns:
        Updated lead or 404 if not found
    """
    try:
        # Verify lead exists first
        client.get_record(AIRTABLE_TABLE, lead_id)
        
        # Update the lead (only non-None fields)
        update_data = lead.model_dump(by_alias=True, exclude_none=True)
        response = client.update_record(AIRTABLE_TABLE, lead_id, update_data)
        return _airtable_record_to_lead_read(response)
    
    except Exception as e:
        if "404" in str(e) or "NOT_FOUND" in str(e):
            raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
        raise HTTPException(status_code=500, detail=f"Error updating lead: {str(e)}")

