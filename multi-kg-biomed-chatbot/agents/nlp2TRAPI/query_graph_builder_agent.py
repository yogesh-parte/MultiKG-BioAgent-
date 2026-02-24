from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext



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
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Optional

ONTOGPT_BIN = os.path.join(os.path.dirname(sys.executable), "ontogpt")

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

    cmd = [ONTOGPT_BIN, "extract", "-t", template, "-i", input_path, "--output-format", "json"]

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
# STEP 3: Detect query type from question
# ---------------------------------------------------------------------


def detect_query_type(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["gene", "genes", "genetic", "mutation", "variant"]):
        return "gene_disease"
    if any(w in q for w in ["phenotype", "symptom", "symptoms", "feature"]):
        return "phenotype_disease"
    return "gene_disease"  # default for Monarch KG


# ---------------------------------------------------------------------
# STEP 4: Build TRAPI 1.4 Query Graph
# ---------------------------------------------------------------------


def build_trapi_query(disease_curie: str, query_type: str, cfg: NLP2TRAPIConfig) -> Dict[str, Any]:
    """
    TRAPI 1.4 format (categories as lists) for Monarch KG.
    Supports gene_disease, phenotype_disease, and drug_disease patterns.
    """
    if query_type == "gene_disease":
        return {
            "message": {
                "query_graph": {
                    "nodes": {
                        "n0": {"ids": [disease_curie], "categories": ["biolink:Disease"]},
                        "n1": {"categories": ["biolink:Gene"]},
                    },
                    "edges": {
                        "e0": {
                            "subject": "n1",
                            "object": "n0",
                            "predicates": ["biolink:gene_associated_with_condition"],
                        }
                    },
                }
            }
        }
    elif query_type == "phenotype_disease":
        return {
            "message": {
                "query_graph": {
                    "nodes": {
                        "n0": {"ids": [disease_curie], "categories": ["biolink:Disease"]},
                        "n1": {"categories": ["biolink:PhenotypicFeature"]},
                    },
                    "edges": {
                        "e0": {
                            "subject": "n0",
                            "object": "n1",
                            "predicates": ["biolink:has_phenotype"],
                        }
                    },
                }
            }
        }
    else:  # drug_disease (default)
        return {
            "message": {
                "query_graph": {
                    "nodes": {
                        "n0": {"ids": [disease_curie], "categories": ["biolink:Disease"]},
                        "n1": {"categories": ["biolink:ChemicalEntity"]},
                    },
                    "edges": {
                        "e0": {
                            "subject": "n1",
                            "object": "n0",
                            "predicates": ["biolink:treats"],
                        }
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
        query_type = detect_query_type(question)
        trapi_query = build_trapi_query(disease_curie, query_type, self.cfg)

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


def build_and_store_trapi_query(question: str, tool_context: ToolContext) -> dict:
    """
    Extract disease entity from question, build a TRAPI 1.4 query dict,
    and store it directly in session state as a structured dict (not text).

    Stores result under session state key 'trapi_query'.
    Returns a status dict to the LLM.
    """
    cfg = _nlp2trapi.cfg

    # Step 1: OntoGPT extraction
    og_output = run_ontogpt_extract(question, cfg.ontogpt_template)
    if "error" in og_output:
        return {"status": "error", "reason": og_output["error"]}

    # Step 2: Extract disease CURIE
    disease_curie = extract_disease_curie(og_output)
    if not disease_curie:
        return {"status": "error", "reason": "No disease CURIE found in OntoGPT output."}

    # Step 3: Detect query type directly from the question
    query_type = detect_query_type(question)
    trapi_query = build_trapi_query(disease_curie, query_type, cfg)

    # Step 4: Write dict directly to session state — no LLM text involved
    tool_context.state["disease_curie"] = disease_curie
    tool_context.state["trapi_query"] = trapi_query
    tool_context.state["query_type"] = query_type

    return {"status": "ok", "disease_curie": disease_curie, "query_type": query_type}

root_agent = Agent(
    model=LiteLlm(model="gpt-4o-mini"),
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