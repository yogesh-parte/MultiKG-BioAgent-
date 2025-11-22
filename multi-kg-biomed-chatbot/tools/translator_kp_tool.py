# tools/translator_kp_tool.py
#All these smart-api URLs (Clinical Connections, BigGIM, etc.) are Translator KPs; most present TRAPI /query
from typing import Dict, Any
from .http_utils import post_json

class TranslatorKPClient:
  def __init__(self, base_url: str):
    # usually base_url like "https://<host>/query" or "https://<host>/trapi/v1.4/query"
    self.base_url = base_url

  async def query(self, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a TRAPI message to this KP and return TRAPI response.
    """
    return await post_json(self.base_url, message)