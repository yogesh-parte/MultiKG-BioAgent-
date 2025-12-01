from google.adk.agents.llm_agent import Agent



"""
NLP2TRAPI Agent (OntoGPT-only version)
--------------------------------------

Pipeline:
    User Question
        → OntoGPT extraction (drug_to_disease)
        → Extract grounded Disease CURIE
        → Build TRAPI 1.1 Query Graph

No NER model is used. OntoGPT performs:
    • Entity extraction
    • Ontology grounding
    • CURIE selection

Outputs:
    {
        "question": ...,
        "disease_phrase": ...,
        "disease_curie": ...,
        "trapi_query": {...},
        "ontogpt_output": {...}
    }

This agent stops BEFORE the TRAPI call.
Production can pass trapi_query to your async httpx client.
"""

import json
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bmt import Toolkit

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------


@dataclass
class NLP2TRAPIConfig:
    ontogpt_template: str = "drug_to_disease"

    biolink_model_url: str = (
        "https://raw.githubusercontent.com/biolink/biolink-model/master/biolink-model.yaml"
    )
    disease_category: str = "biolink:Disease"
    drug_category: str = "biolink:ChemicalSubstance"
    treats_predicate: str = "biolink:treats"


# ---------------------------------------------------------------------
# STEP 1: OntoGPT extraction & grounding
# ---------------------------------------------------------------------


def run_ontogpt_extract(text: str, template: str) -> Dict[str, Any]:
    """
    Run OntoGPT CLI extraction.
    Requires ontogpt installed: pip install ontogpt
    """
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        f.write(text)
        f.flush()
        input_path = f.name

    cmd = [
        "ontogpt",
        "extract",
        "-t",
        template,
        "-i",
        input_path,
        "--output-format",
        "json",
    ]

    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip()
        return json.loads(output) if output else {}
    except Exception as e:
        return {"error": f"OntoGPT execution failed: {str(e)}"}


# ---------------------------------------------------------------------
# STEP 2: Extract disease CURIE from OntoGPT JSON
# ---------------------------------------------------------------------


def extract_disease_curie(og: Dict[str, Any]) -> Optional[str]:
    """
    Extract a disease CURIE from OntoGPT output.
    Supports:
        • extracted_object["diseases"] = ["MONDO:0005148"]
        • named_entities → [{"id": "..."}]
        • deep id+label structures
    """
    if not og or "extracted_object" not in og:
        return None

    eo = og["extracted_object"]

    # ----------------------------------------
    # 1) If OntoGPT template produced diseases list
    # ----------------------------------------
    if "diseases" in eo and isinstance(eo["diseases"], list):
        if len(eo["diseases"]) > 0:
            return eo["diseases"][0]

    # ----------------------------------------
    # 2) Try named entities list
    # ----------------------------------------
    if "named_entities" in og:
        for ent in og["named_entities"]:
            if "id" in ent:
                return ent["id"]

    # ----------------------------------------
    # 3) Deep search fallback for id+label pairs
    # ----------------------------------------
    candidates = []

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and "label" in o:
                candidates.append(o["id"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(eo)
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------
# STEP 3: Build TRAPI 1.1 Query Graph
# ---------------------------------------------------------------------


def build_trapi_query(disease_curie: str, cfg: NLP2TRAPIConfig) -> Dict[str, Any]:
    """
    TRAPI 1.1 format expected by ROBOKOP/AUTOMAT:
        Drug --treats--> Disease
    """
    return {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {"ids": [disease_curie], "category": cfg.disease_category},
                    "n1": {"category": cfg.drug_category},
                },
                "edges": {
                    "e0": {"subject": "n1", "object": "n0", "predicate": cfg.treats_predicate}
                },
            }
        }
    }


# ---------------------------------------------------------------------
# MAIN AGENT (no NER, OntoGPT-only)
# ---------------------------------------------------------------------


class NLP2TRAPIAgent:
    """
    A simple agent:
        question → OntoGPT → disease CURIE → TRAPI Query Graph
    """

    def __init__(self, config: Optional[NLP2TRAPIConfig] = None):
        self.cfg = config or NLP2TRAPIConfig()
        self.bmt = Toolkit(self.cfg.biolink_model_url)

    def process_question(self, question: str) -> Dict[str, Any]:
        # -------------------------------------------------------------
        # Step 1: OntoGPT extraction
        # -------------------------------------------------------------
        og_output = run_ontogpt_extract(
            question,
            self.cfg.ontogpt_template,
        )

        if "error" in og_output:
            return {
                "question": question,
                "error": og_output["error"],
                "ontogpt_output": og_output,
            }

        # -------------------------------------------------------------
        # Step 2: Extract disease CURIE
        # -------------------------------------------------------------
        disease_curie = extract_disease_curie(og_output)

        if not disease_curie:
            return {
                "question": question,
                "error": "No CURIE found in OntoGPT output.",
                "ontogpt_output": og_output,
            }

        # -------------------------------------------------------------
        # Step 3: Build TRAPI query graph
        # -------------------------------------------------------------
        trapi_query = build_trapi_query(disease_curie, self.cfg)

        return {
            "question": question,
            "trapi_query": trapi_query,
        }


_nlp2trapi = NLP2TRAPIAgent()

def build_trapi_from_question(question: str) -> dict:
    """
    Convert a natural language biomedical question into:

    - grounded disease CURIE
    - TRAPI 1.1 query graph
    - raw OntoGPT output

    This tool does NOT call any TRAPI endpoint; it only builds the query.
    """
    return _nlp2trapi.process_question(question)

root_agent = Agent(
    model="gemini-2.5-flash",  # or whatever model you’re standardizing on
    name="nlp2trapi_root_agent",
    description=(
        "Converts biomedical treatment questions into TRAPI 1.1 query graphs "
        "using OntoGPT's drug_to_disease template."
    ),
    instruction="""
You are a biomedical query planner that turns natural language questions
about drugs that treat diseases into TRAPI 1.1 query graphs.

When the user asks about drugs that treat a disease (e.g. 'What drugs treat
metastatic prostate cancer?'), you MUST call the 'build_trapi_from_question'
tool.

Use the tool output as follows:
- If it returns an error, explain the error and ask the user to rephrase.
- If it returns a disease_curie and trapi_query, show the TRAPI JSON and give
  a short explanation of which disease CURIE you used.

You never call TRAPI KPs or ARAs yourself; you only build the query.
""",
    tools=[build_trapi_from_question],
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="nlp2trapi_root_agent",
    description="Converts biomedical questions directly into TRAPI 1.1 Query Graphs.",
    instruction="""
You are an NLP→TRAPI agent.

When the user asks anything related to drugs that treat a disease,
use the 'build_trapi_from_question' tool.

The tool returns ONLY a TRAPI query graph.
Do NOT wrap it in extra text. Just return the TRAPI JSON.
""",
    tools=[build_trapi_from_question],
)