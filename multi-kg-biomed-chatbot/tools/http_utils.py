# tools/http_utils.py
import httpx
from typing import Any, Dict

async def post_json(url: str, payload: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
  async with httpx.AsyncClient(timeout=timeout) as client:
    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()