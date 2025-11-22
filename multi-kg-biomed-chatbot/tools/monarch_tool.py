# tools/monarch_tool.py
# Monarch’s FastAPI exposes entity & association endpoints
# see: https://monarch-app.monarchinitiative.org/FastAPI/
from typing import Dict, Any, Optional
import httpx

MONARCH_BASE = "https://monarch-app.monarchinitiative.org/v3/api"

async def monarch_get_entity(curie: str) -> Dict[str, Any]:
  """
  Get a Monarch entity by CURIE (e.g. MONDO:0005148, HGNC:6284).
  """
  url = f"{MONARCH_BASE}/entity/{curie}"
  async with httpx.AsyncClient() as client:
    r = await client.get(url)
    r.raise_for_status()
    return r.json()

async def monarch_get_associations(
    subject: Optional[str] = None,
    object: Optional[str] = None,
    predicate: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
  """
  Query Monarch association endpoint using subject/object/predicate/category filters.
  """
  params = {
    "subject": subject,
    "object": object,
    "predicate": predicate,
    "category": category,
    "limit": limit
  }
  # remove None values
  params = {k: v for k, v in params.items() if v is not None}
  url = f"{MONARCH_BASE}/association"
  async with httpx.AsyncClient() as client:
    r = await client.get(url, params=params)
    r.raise_for_status()
    return r.json()