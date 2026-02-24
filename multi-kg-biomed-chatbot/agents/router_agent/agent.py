from typing import List, Literal, Optional

from pydantic import BaseModel
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext


# ---------------------------------------------------------------------------
# Step 1: KG routing table and QueryPlan schema
# ---------------------------------------------------------------------------

_PREDICATE_MAP = {
    "gene_disease": "biolink:gene_associated_with_condition",
    "phenotype_disease": "biolink:has_phenotype",
    "drug_disease": "biolink:treats",
}

_KG_MAP = {
    "gene_disease":      ["monarch", "biggim"],
    "phenotype_disease": ["monarch", "clinical_connections"],
    "drug_disease":      ["clinical_connections", "drug_approvals"],
}


class QueryPlan(BaseModel):
    question: str
    query_type: Literal["gene_disease", "phenotype_disease", "drug_disease"]
    target_kgs: List[str]
    predicate: str
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Step 2: route_question — pure Python tool, no KG calls
# ---------------------------------------------------------------------------

def route_question(question: str, tool_context: ToolContext) -> dict:
    """
    Read the query_type already stored by nlp_trapi_agent and set target_kgs.

    Stores:
      - state["query_plan"]  — full QueryPlan dict
      - state["target_kgs"]  — list of KG names to query
      - state["query_type"]  — string (re-set for safety)

    Returns a small status dict to the LLM.
    """
    # Read query_type set by nlp_trapi_agent
    query_type = tool_context.state.get("query_type")
    if not query_type:
        # Fallback: classify from question text if nlp_trapi_agent didn't run
        q = question.lower()
        if any(w in q for w in ["drug", "drugs", "treat", "treats", "treatment", "medication", "therapy", "inhibitor"]):
            query_type = "drug_disease"
        elif any(w in q for w in ["phenotype", "symptom", "symptoms", "sign", "signs", "feature", "manifestation"]):
            query_type = "phenotype_disease"
        else:
            query_type = "gene_disease"

    target_kgs = _KG_MAP.get(query_type, ["monarch"])

    plan = QueryPlan(
        question=question,
        query_type=query_type,
        target_kgs=target_kgs,
        predicate=_PREDICATE_MAP[query_type],
    )

    tool_context.state["query_plan"] = plan.model_dump()
    tool_context.state["target_kgs"] = target_kgs
    # Note: query_type already in state from nlp_trapi_agent, but set again for safety
    tool_context.state["query_type"] = query_type

    return {"ok": True, "query_type": query_type, "target_kgs": target_kgs}


# ---------------------------------------------------------------------------
# Step 3: router_agent — calls the tool, reports status
# ---------------------------------------------------------------------------

router_agent = LlmAgent(
    name="router_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Classifies biomedical questions and stores a multi-KG query plan in session state.",
    instruction="""
You are a biomedical query router. Call 'route_question' with the user's question.

- Respond with exactly:
  OK: routing <query_type> query to <target_kgs>
""",
    tools=[route_question],
    output_key="router_status",
)
