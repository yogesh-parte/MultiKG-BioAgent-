from typing import Literal, Optional

from pydantic import BaseModel
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext


# ---------------------------------------------------------------------------
# Step 1: QueryPlan schema
# ---------------------------------------------------------------------------

_PREDICATE_MAP = {
    "gene_disease": "biolink:gene_associated_with_condition",
    "phenotype_disease": "biolink:has_phenotype",
    "drug_disease": "biolink:treats",
}


class QueryPlan(BaseModel):
    question: str
    query_type: Literal["gene_disease", "phenotype_disease", "drug_disease"]
    target_kg: Literal["monarch", "unsupported"]
    predicate: str
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Step 2: route_question — pure Python tool, no KG calls
# ---------------------------------------------------------------------------

def route_question(question: str, tool_context: ToolContext) -> dict:
    """
    Classify the biomedical question, choose the target KG, and store a
    structured QueryPlan in session state.

    Stores:
      - state["query_plan"]  — full QueryPlan dict
      - state["query_type"]  — string (used by callbacks and TRAPI builder)
      - state["target_kg"]   — string

    Returns a small status dict to the LLM.
    """
    q = question.lower()

    if any(w in q for w in ["drug", "drugs", "treat", "treats", "treatment", "medication", "therapy", "inhibitor"]):
        query_type = "drug_disease"
    elif any(w in q for w in ["gene", "genes", "genetic", "mutation", "variant", "locus"]):
        query_type = "gene_disease"
    elif any(w in q for w in ["phenotype", "symptom", "symptoms", "sign", "signs", "feature", "manifestation"]):
        query_type = "phenotype_disease"
    else:
        query_type = "gene_disease"  # default for Monarch KG

    target_kg = "unsupported" if query_type == "drug_disease" else "monarch"
    notes = (
        "Drug-disease queries require a drug KG (e.g. ChEMBL, MolePro). "
        "Monarch KG does not contain 'biolink:treats' edges."
        if query_type == "drug_disease"
        else None
    )

    plan = QueryPlan(
        question=question,
        query_type=query_type,
        target_kg=target_kg,
        predicate=_PREDICATE_MAP[query_type],
        notes=notes,
    )

    tool_context.state["query_plan"] = plan.model_dump()
    tool_context.state["query_type"] = query_type
    tool_context.state["target_kg"] = target_kg

    return {"ok": True, "query_type": query_type, "target_kg": target_kg}


# ---------------------------------------------------------------------------
# Step 3: router_agent — calls the tool, reports status
# ---------------------------------------------------------------------------

router_agent = LlmAgent(
    name="router_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Classifies biomedical questions and stores a query plan in session state.",
    instruction="""
You are a biomedical query router. Call 'route_question' with the user's question.

- If the result has target_kg == 'unsupported', respond with exactly:
  ERROR: Drug queries are not yet supported. Monarch KG only covers gene and phenotype associations. Try asking: "Which genes are associated with <disease>?"
- Otherwise respond with exactly:
  OK: routing <query_type> query to <target_kg>
""",
    tools=[route_question],
    output_key="router_status",
)
