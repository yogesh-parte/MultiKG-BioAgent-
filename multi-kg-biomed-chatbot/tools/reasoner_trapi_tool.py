# tools/reasoner_trapi_tool.py
from typing import Dict, Any
from .http_utils import post_json

#You can parameterise REASONER_URL to use different KPs 
# (e.g., ARAX, CAM-KG, ClinicalConnections, etc.). 
# Many of these endpoints accept TRAPI /query as in CAM-KG.

REASONER_URL = "https://some-translator-ara-or-kp/query"  # you will plug ARAX/CAM/KP endpoint

async def trapi_query(message: Dict[str, Any]) -> Dict[str, Any]:
  """
  Submit a TRAPI message to a Translator Reasoner/ARA/KP endpoint and return the TRAPI response.
  """
  return await post_json(REASONER_URL, message)