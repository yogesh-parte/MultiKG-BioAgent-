from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from nlp2TRAPI.query_graph_builder_agent import build_and_store_trapi_query
from kg_orchestrator.agent import kg_orchestrator
from evidence_merger_agent.agent import evidence_merger_agent
from trapi_nlp_answer_agent.agent import explain_agent


nlp_trapi_agent = LlmAgent(
    model=LiteLlm(model="gpt-4o-mini"),
    name="nlp2trapi_agent",
    description=(
        "Extracts disease entity from question and stores a TRAPI query dict in session state."
    ),
    instruction="""
You are a biomedical query planner. When the user asks a biomedical question, call the 'build_and_store_trapi_query' tool with the question.

- If the tool returns status 'error', respond with: ERROR: <reason>
- If the tool returns status 'ok', respond with: OK: extracted <disease_curie> as <query_type>
""",
    tools=[build_and_store_trapi_query],
)


root_agent = SequentialAgent(
    name="biomed_kg_chatbot_agent",
    sub_agents=[
        nlp_trapi_agent,
        kg_orchestrator,
        evidence_merger_agent,
        explain_agent,
    ],
)
