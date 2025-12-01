from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent

from nlp2TRAPI.query_graph_builder_agent import build_trapi_from_question
from monarch_agent.agent import query_monarch_trapi
from trapi_nlp_answer_agent.agent import extract_trapi_triples
from pydantic import BaseModel
from trapi_nlp_answer_agent.agent import explain_agent

class TrapiQueryInput(BaseModel):
    trapi_query: dict
    question: str

class MonarchTrapiOutput(BaseModel):
    trapi_response: dict

nlp_trapi_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="nlp2trapi_agent",
    description=(
        "Converts biomedical questions into TRAPI 1.1 query graphs "
        "using OntoGPT's drug_to_disease template."
    ),
    instruction="""
You are a biomedical query planner that turns natural language questions  into TRAPI 1.1 query graphs.The trapi_query is provided in the session state under the key 'trapi_query'.

When the user asks any biomedical questions, you MUST call the 'build_trapi_from_question'
tool.

Use the tool output as follows:
- If it returns an error, explain the error and ask the user to rephrase.
- If it returns a dictionary  trapi_query and question, Return the trapi_query as the final output.


  

""",
    tools=[build_trapi_from_question],
    output_key="trapi_query",
)

monarch_agent = LlmAgent(
    name="monarch_agent",
    model="gemini-2.5-flash",
    input_schema=TrapiQueryInput,
    instruction=(
        "You are a biomedical knowledge graph agent that operates ONLY on the output of the NLP2TRAPI agent.\n\n"

        "The trapi_query is provided in the session state under the key 'trapi_query'."

        "Your job:\n"
        "1. Extract the `trapi_query` "
        "2. Call the `query_monarch_trapi` tool using ONLY this `trapi_query` value.\n"
        "   Do NOT modify, transform, extend, or rebuild the TRAPI query.\n"
        "   Do NOT propose TRAPI queries yourself.\n\n"

        "return the full TRAPI response from Monarch-KG as the final output"



        "STRICT RULES:\n"
        "- Never generate TRAPI queries.\n"
        "- Never interpret raw natural language from the user.\n"
        "- Always rely exclusively on `trapi_query` from the NLP2TRAPI agent.\n"
        "- Use the `question` key only to guide your explanation, not as input to any tool.\n"
    ),
    tools=[query_monarch_trapi],
    output_key="Monarch_output"
)



root_agent = SequentialAgent(
    name="biomed_kg_chatbot_agent",
    sub_agents=[nlp_trapi_agent, monarch_agent, explain_agent],
)
