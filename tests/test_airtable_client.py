import os
import pytest


def test_airtable_client_env_missing():
    from backend.airtable_client import AirtableClient

    old_key = os.environ.pop("AIRTABLE_API_KEY", None)
    old_base = os.environ.pop("AIRTABLE_BASE_ID", None)
    try:
        with pytest.raises(ValueError):
            AirtableClient()
    finally:
        if old_key:
            os.environ["AIRTABLE_API_KEY"] = old_key
        if old_base:
            os.environ["AIRTABLE_BASE_ID"] = old_base
