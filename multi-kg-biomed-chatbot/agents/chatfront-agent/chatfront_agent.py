# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from agents.query_graph_builder_agent import QueryGraphBuilderAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.evidence_merger_agent import merge_evidence
from agents.explanation_agent import ExplanationAgent

app = FastAPI()

qg_builder = QueryGraphBuilderAgent()
orchestrator = OrchestratorAgent(
  clinical_connections_url="https://<clinical-connections-trapi>/query",
  biggim_url="https://<biggim-trapi>/query",
  drug_approvals_url="https://<drug-approvals-trapi>/query",
  clinical_trials_url="https://<trials-trapi>/query",
  wellness_multiomics_url="https://<multiomics-trapi>/query"
)
explainer = ExplanationAgent()

class ChatRequest(BaseModel):
  question: str
  history: list = []

@app.post("/chat")
async def chat(req: ChatRequest):
  trapi_msg = await qg_builder.build(req.question)
  kg_result = await orchestrator.handle(trapi_msg)
  merged = merge_evidence(kg_result["responses"])
  answer = await explainer.explain(req.question, merged)
  return {
    "answer": answer,
    "debug": {
      "trapi_message": trapi_msg,
      "kg_calls": kg_result["kg_calls"],
    }
  }