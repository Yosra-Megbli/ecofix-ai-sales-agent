"""Airtable client wrapper for basic CRUD operations."""

from dotenv import load_dotenv
load_dotenv()

import os
import requests
from typing import Any, Dict, Optional


class AirtableClient:
    def __init__(self, api_key: Optional[str] = None, base_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("AIRTABLE_API_KEY")
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID")
        if not self.api_key or not self.base_id:
            raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in environment")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _table_url(self, table_name: str) -> str:
        return f"{self.base_url}/{requests.utils.quote(table_name, safe='')}"

    def list_records(self, table_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        url = self._table_url(table_name)
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        url = f"{self._table_url(table_name)}/{record_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def create_record(self, table_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        url = self._table_url(table_name)
        payload = {"fields": fields}
        resp = requests.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def update_record(self, table_name: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._table_url(table_name)}/{record_id}"
        payload = {"fields": fields}
        resp = requests.patch(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def find_by_field(self, table_name: str, field_name: str, value: str) -> Optional[Dict[str, Any]]:
        formula = f"{{{field_name}}} = '{value.replace('"', '\\"')}'"
        params = {"filterByFormula": formula, "maxRecords": 1}
        data = self.list_records(table_name, params=params)
        records = data.get("records", [])
        return records[0] if records else None
