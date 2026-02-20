from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
import json

from nlp2TRAPI.query_graph_builder_agent import build_and_store_trapi_query
from monarch_agent.agent import query_monarch_trapi
from trapi_nlp_answer_agent.agent import extract_trapi_triples
from trapi_nlp_answer_agent.agent import explain_agent


def run_monarch_query(tool_context: ToolContext) -> dict:
    """Query Monarch KG using the trapi_query stored in session state. Call with no arguments."""
    trapi_query = tool_context.state.get("trapi_query")
    if not trapi_query:
        return {"error": "No trapi_query found in session state"}

    if not isinstance(trapi_query, dict):
        return {
            "error": "trapi_query must be a dict (structured TRAPI request).",
            "type": str(type(trapi_query)),
        }

    msg = trapi_query.get("message")
    qg = msg.get("query_graph") if isinstance(msg, dict) else None
    if not qg:
        return {"error": "Invalid TRAPI: missing message.query_graph"}

    return query_monarch_trapi(trapi_query)

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

monarch_agent = LlmAgent(
    name="monarch_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    instruction=(
        "You are a biomedical knowledge graph agent.\n\n"
        "Your ONLY job: call the `run_monarch_query` tool with NO arguments. "
        "It will read the TRAPI query from session state and query Monarch KG automatically.\n\n"
        "Do NOT pass any arguments to `run_monarch_query`.\n"
        "Do NOT generate or modify TRAPI queries yourself.\n"
        "Return the full tool response as your final output."
    ),
    tools=[run_monarch_query],
    output_key="Monarch_output"
)



root_agent = SequentialAgent(
    name="biomed_kg_chatbot_agent",
    sub_agents=[nlp_trapi_agent, monarch_agent, explain_agent],
)
