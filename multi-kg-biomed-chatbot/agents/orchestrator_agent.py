# agents/orchestrator_agent.py
# End to end orchestrator agent 
from typing import Dict, Any, List
from tools.monarch_tool import monarch_get_associations
from tools.translator_kp_tool import TranslatorKPClient

class OrchestratorAgent:
  def __init__(
      self,
      clinical_connections_url: str,
      biggim_url: str,
      drug_approvals_url: str,
      clinical_trials_url: str,
      wellness_multiomics_url: str
  ):
    self.clinical_conn_kp = TranslatorKPClient(clinical_connections_url)
    self.biggim_kp = TranslatorKPClient(biggim_url)
    self.drug_approvals_kp = TranslatorKPClient(drug_approvals_url)
    self.clinical_trials_kp = TranslatorKPClient(clinical_trials_url)
    self.wellness_kp = TranslatorKPClient(wellness_multiomics_url)

  async def handle(self, trapi_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspect query_graph and decide which KPs to call.
    """
    qg = trapi_message.get("message", {}).get("query_graph", {})
    # naive intent detection: look at categories/predicates
    predicates = list(qg.get("edges", {}).values())[0].get("predicates", [])
    nodes = qg.get("nodes", {})

    wants_drugs = any("treats" in p for p in predicates) or \
                  any("biolink:Drug" in c for n in nodes.values()
                      for c in n.get("categories", []))

    wants_genes = any("biolink:Gene" in c for n in nodes.values()
                      for c in n.get("categories", []))

    responses: List[Dict[str, Any]] = []
    kg_calls: List[Dict[str, Any]] = []

    # Monarch: disease-gene, disease-phenotype, etc.
    # extract a disease id if present
    disease_ids = [
      n.get("ids", [None])[0]
      for n in nodes.values()
      if "biolink:Disease" in n.get("categories", [])
      and n.get("ids")
    ]
    disease_id = disease_ids[0] if disease_ids else None

    if disease_id and wants_genes:
      # Example: Monarch disease->gene via associations
      monarch_resp = await monarch_get_associations(
        subject=None,
        object=disease_id,
        predicate=None,
        category="biolink:GeneToDiseaseAssociation",
        limit=100
      )
      responses.append({"source": "monarch", "data": monarch_resp})
      kg_calls.append({"kp": "monarch", "mode": "association"})

    # Clinical Connections KP via TRAPI
    clinical_resp = await self.clinical_conn_kp.query(trapi_message)
    responses.append({"source": "clinical_connections", "data": clinical_resp})
    kg_calls.append({"kp": "clinical_connections", "mode": "trapi"})

    # BigGIM for drug response / omics
    if wants_drugs or wants_genes:
      biggim_resp = await self.biggim_kp.query(trapi_message)
      responses.append({"source": "biggim", "data": biggim_resp})
      kg_calls.append({"kp": "biggim", "mode": "trapi"})

    # Drug approvals
    if wants_drugs:
      approvals_resp = await self.drug_approvals_kp.query(trapi_message)
      responses.append({"source": "drug_approvals", "data": approvals_resp})
      kg_calls.append({"kp": "drug_approvals", "mode": "trapi"})

    # Clinical trials
    trials_resp = await self.clinical_trials_kp.query(trapi_message)
    responses.append({"source": "clinical_trials", "data": trials_resp})
    kg_calls.append({"kp": "clinical_trials", "mode": "trapi"})

    # Wellness omics if gene-heavy
    if wants_genes:
      wellness_resp = await self.wellness_kp.query(trapi_message)
      responses.append({"source": "wellness_multiomics", "data": wellness_resp})
      kg_calls.append({"kp": "wellness_multiomics", "mode": "trapi"})

    return {
      "kg_calls": kg_calls,
      "responses": responses,
    }