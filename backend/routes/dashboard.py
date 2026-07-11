"""Routes for dashboard statistics."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from backend.airtable_client import AirtableClient

router = APIRouter()
client = AirtableClient()

def fetch_all_records(table_name: str) -> List[Dict[str, Any]]:
    """Fetch all records from an Airtable table handling pagination."""
    records = []
    offset = None
    while True:
        params = {}
        if offset:
            params["offset"] = offset
        try:
            data = client.list_records(table_name, params=params)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch records from table '{table_name}': {str(e)}")
        
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records

@router.get("/stats")
async def get_dashboard_stats():
    """
    Get dashboard statistics dynamically from Airtable.
    Returns counts of total leads, leads by status, total conversations,
    qualified/unqualified leads, and open/closed conversations.
    """
    try:
        # Fetch all leads and conversations
        leads_records = fetch_all_records("Leads")
        conv_records = fetch_all_records("Conversations")
        
        total_leads = len(leads_records)
        total_conversations = len(conv_records)
        
        # Build map of Lead ID to Status
        lead_id_to_status = {}
        for record in leads_records:
            lead_id_to_status[record.get("id")] = record.get("fields", {}).get("Statut", "New")
            
        # Count by status
        status_counts = {
            "New": 0,
            "Contacted": 0,
            "Replied": 0,
            "Qualified": 0,
            "Appointment": 0,
            "Contract Sent": 0,
            "Sold": 0,
            "Rejected": 0
        }
        
        contacted_plus_count = 0
        contacted_plus_statuses = {"Contacted", "Replied", "Qualified", "Appointment", "Contract Sent", "Sold"}
        
        qualified_leads_count = 0
        unqualified_leads_count = 0
        
        qualified_statuses = {"Qualified", "Appointment", "Contract Sent", "Sold"}
        
        for record in leads_records:
            fields = record.get("fields", {})
            status = fields.get("Statut", "New")
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[status] = status_counts.get(status, 0) + 1
                
            if status in contacted_plus_statuses:
                contacted_plus_count += 1
                
            if status in qualified_statuses:
                qualified_leads_count += 1
            elif status == "Rejected":
                unqualified_leads_count += 1
                
        conversion_rate = 0.0
        if total_leads > 0:
            conversion_rate = round((contacted_plus_count / total_leads) * 100, 1)
            
        # Count open vs closed conversations
        open_statuses = {"New", "Contacted", "Replied"}
        open_conversations_count = 0
        closed_conversations_count = 0
        
        for record in conv_records:
            fields = record.get("fields", {})
            lead_links = fields.get("Lead", [])
            if lead_links:
                lead_id = lead_links[0]
                status = lead_id_to_status.get(lead_id, "New")
                if status in open_statuses:
                    open_conversations_count += 1
                else:
                    closed_conversations_count += 1
            else:
                # No lead link is considered open conversation
                open_conversations_count += 1
                
        return {
            "total_leads": total_leads,
            "total_conversations": total_conversations,
            "conversion_rate": conversion_rate,
            "status_counts": status_counts,
            "qualified_leads": qualified_leads_count,
            "unqualified_leads": unqualified_leads_count,
            "open_conversations": open_conversations_count,
            "closed_conversations": closed_conversations_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur de connexion à Airtable : {str(e)}"
        )
