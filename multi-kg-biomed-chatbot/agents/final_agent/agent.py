from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext
import json

from nlp2TRAPI.query_graph_builder_agent import build_trapi_from_question
from monarch_agent.agent import query_monarch_trapi
from trapi_nlp_answer_agent.agent import extract_trapi_triples
from trapi_nlp_answer_agent.agent import explain_agent


def run_monarch_query(tool_context: ToolContext) -> dict:
    """Query Monarch KG using the trapi_query stored in session state. Call with no arguments."""
    raw = tool_context.state.get("trapi_query")
    if not raw:
        return {"error": "No trapi_query found in session state"}
    if isinstance(raw, str):
        # Strip markdown code fences if the LLM wrapped the JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        # Find start of JSON object
        if "{" in raw:
            raw = raw[raw.index("{"):]
        try:
            # raw_decode tolerates trailing text/newlines after the JSON
            raw, _ = json.JSONDecoder().raw_decode(raw.strip())
        except json.JSONDecodeError:
            return {"error": f"Could not parse trapi_query as JSON: {raw[:200]}"}
    return query_monarch_trapi(raw)

nlp_trapi_agent = LlmAgent(
    model=LiteLlm(model="gpt-4o-mini"),
    name="nlp2trapi_agent",
    description=(
        "Converts biomedical questions into TRAPI 1.1 query graphs "
        "using OntoGPT's drug_to_disease template."
    ),
    instruction="""
You are a biomedical query planner. When the user asks a biomedical question, call the 'build_trapi_from_question' tool.

- If the tool returns an error, respond with just: ERROR: <reason>
- If the tool returns a trapi_query, respond with ONLY the raw JSON of trapi_query — no explanation, no markdown fences, no extra text. Just the JSON object starting with {.
""",
    tools=[build_trapi_from_question],
    output_key="trapi_query",
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
