"""
KG Orchestrator
---------------
LlmAgent that calls route_question to determine query type, then invokes
the appropriate KG sub-agents via AgentTool in the correct order.

Replaces the 10-step SequentialAgent + skip-guard pattern with a single
LlmAgent that only calls the KG agents it actually needs.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from router_agent.agent import route_question
from monarch_agent.agent import monarch_agent
from clinical_connections_agent.agent import clinical_connections_agent
from biggim_agent.agent import biggim_agent
from drug_approvals_agent.agent import drug_approvals_agent
from clinical_trials_agent.agent import clinical_trials_agent
from wellness_multiomics_agent.agent import wellness_multiomics_agent

kg_orchestrator = LlmAgent(
    name="kg_orchestrator",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Routes biomedical queries to the correct KG agents and calls them in order.",
    instruction="""
You are a biomedical KG orchestrator. Follow these steps exactly:

Step 1: Call route_question with the user's original question to get query_type and target_kgs.

Step 2: Based on query_type, call the appropriate KG agents IN ORDER:
  - gene_disease:       call monarch_agent THEN biggim_agent
  - phenotype_disease:  call monarch_agent THEN clinical_connections_agent
  - drug_disease:       call clinical_connections_agent only

Rules:
- Each agent reads its inputs from session state automatically.
  Send only a brief task description string (e.g. "Query for gene-disease associations").
- For gene_disease, monarch_agent runs first and stores gene CURIEs in state.
  biggim_agent then reads those CURIEs — it will skip itself if none were found.
- Do NOT call stub agents (drug_approvals_agent, clinical_trials_agent,
  wellness_multiomics_agent) — they are not yet configured and will return skipped responses.
- After all relevant KG agents have been called, respond with:
  DONE: queried <comma-separated list of agents called>
""",
    tools=[
        route_question,
        AgentTool(agent=monarch_agent,              skip_summarization=True),
        AgentTool(agent=clinical_connections_agent, skip_summarization=True),
        AgentTool(agent=biggim_agent,               skip_summarization=True),
        AgentTool(agent=drug_approvals_agent,       skip_summarization=True),
        AgentTool(agent=clinical_trials_agent,      skip_summarization=True),
        AgentTool(agent=wellness_multiomics_agent,  skip_summarization=True),
    ],
    output_key="orchestrator_status",
)
