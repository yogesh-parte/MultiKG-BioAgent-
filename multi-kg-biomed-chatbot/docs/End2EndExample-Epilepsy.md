End to example using a real biomedical use case: **Epilepsy → Genes → Drugs → Clinical Trials**.

---

## Part A: Fully-Worked Example Use Case (Epilepsy)

Real disease (MONDO), genes (HGNC), drugs (DrugBank/RxCUI), trials (NCT), and knowledge providers.

### A.1 User Query

```
"What causes epilepsy and what drugs treat it? Also show genes and any trials."
```

### A.2 Query Graph Built by Query-Graph Agent

Query graph compliant with TRAPI 1.4 schema:

```json
{
  "message": {
    "query_graph": {
      "nodes": {
        "n0": {
          "ids": ["MONDO:0005151"],
          "categories": ["biolink:Disease"]
        },
        "n1": {
          "categories": ["biolink:Gene"]
        },
        "n2": {
          "categories": ["biolink:Drug"]
        }
      },
      "edges": {
        "e0": {
          "subject": "n1",
          "object": "n0",
          "predicates": ["biolink:gene_associated_with_condition"]
        },
        "e1": {
          "subject": "n2",
          "object": "n1",
          "predicates": ["biolink:targets"]
        }
      }
    }
  }
}
```

### A.3 Orchestrator Agent Routing Decision

The orchestrator inspects the query graph and determines which KGs to call:

| Need | Predicates | Node Categories | KGs Triggered |
|------|-----------|-----------------|--------------|
| Disease → Gene | `gene_associated_with_condition` | Disease/Gene | Monarch, ClinicalConnections |
| Gene → Drug | `targets` | Gene/Drug | DrugApprovals, BigGIM, Wellness Multiomics, ClinicalConnections |
| Disease → Drug | Implied | Disease/Drug | DrugApprovals, ClinicalTrials |
| Trial Info | Not explicit | — | ClinicalTrials KG |

**Result:** 6 KGs are called automatically.

### A.4 Actual Orchestration Call Map

```json
{
  "kg_calls": [
    { "kp": "monarch", "mode": "association" },
    { "kp": "clinical_connections", "mode": "trapi" },
    { "kp": "biggim", "mode": "trapi" },
    { "kp": "drug_approvals", "mode": "trapi" },
    { "kp": "clinical_trials", "mode": "trapi" },
    { "kp": "wellness_multiomics", "mode": "trapi" }
  ]
}
```

### A.5 Sample TRAPI Responses (Simplified)

#### 1. Monarch Disease-Gene Response

Epilepsy genes identified:

- **SCN1A** (HGNC:10585)
- **DEPDC5** (HGNC:15847)
- **PCDH19** (HGNC:17498)

```json
{
  "message": {
    "knowledge_graph": {
      "nodes": {
        "MONDO:0005151": { 
          "name": "Epilepsy", 
          "categories": ["biolink:Disease"] 
        },
        "HGNC:10585": { 
          "name": "SCN1A", 
          "categories": ["biolink:Gene"] 
        }
      },
      "edges": {
        "e1": {
          "subject": "HGNC:10585",
          "predicate": "biolink:gene_associated_with_condition",
          "object": "MONDO:0005151"
        }
      }
    }
  }
}
```

#### 2. Clinical Connections: Gene ↔ Drug

Example: SCN1A → Sodium channel blocking anti-epileptics

```json
{
  "message": {
    "knowledge_graph": {
      "nodes": {
        "CHEBI:9443": { "name": "Carbamazepine" },
        "HGNC:10585": { "name": "SCN1A" }
      },
      "edges": {
        "e7": {
          "subject": "CHEBI:9443",
          "predicate": "biolink:targets",
          "object": "HGNC:10585"
        }
      }
    }
  }
}
```

#### 3. Drug Approvals KG

FDA-approved epilepsy drugs:

- Valproate
- Topiramate
- Lamotrigine

#### 4. Clinical Trials KG

Mapped trials:

- **NCT05100021** – Valproate study
- **NCT04854251** – Cannabidiol study

### A.6 Evidence Merger Output

Canonical merged knowledge graph after deduplication and score aggregation:

```json
{
  "nodes": {
    "MONDO:0005151": { "name": "Epilepsy" },
    "HGNC:10585": { "name": "SCN1A" },
    "CHEBI:9443": { "name": "Carbamazepine" },
    "CHEBI:3562": { "name": "Valproate" }
  },
  "edges": [
    {
      "subject": "HGNC:10585",
      "predicate": "biolink:gene_associated_with_condition",
      "object": "MONDO:0005151",
      "provenance": ["monarch", "clinical_connections"]
    },
    {
      "subject": "CHEBI:9443",
      "predicate": "biolink:targets",
      "object": "HGNC:10585",
      "provenance": ["clinical_connections", "biggim"]
    },
    {
      "subject": "CHEBI:3562",
      "predicate": "biolink:treats",
      "object": "MONDO:0005151",
      "provenance": ["drug_approvals"]
    }
  ]
}
```

### A.7 Summarization Agent Final Answer

Example LLM output:

> **Epilepsy (MONDO:0005151)** is strongly associated with **SCN1A**, **DEPDC5**, and **PCDH19** according to Monarch and Clinical Connections.
>
> **Mechanisms:**
> - SCN1A encodes a sodium channel involved in neuronal excitability
> - Pathogenic variants lower seizure threshold → epileptic encephalopathies
>
> **Approved Treatments:**
> - Valproate (CHEBI:3562)
> - Topiramate (CHEBI:9473)
> - Carbamazepine (CHEBI:9443) targets SCN1A sodium channels
>
> **Clinical Trials:**
> - Cannabidiol trials (e.g., NCT04854251)
> - Valproate longitudinal studies (NCT05100021)
>
> **Evidence Sources:** Monarch, ClinicalConnections, BigGIM, DrugApprovals, ClinicalTrials, Multiomics.

---

## Part B: Concrete Code Example

Example code for one KG (Monarch):

```python
async def epilepsy_disease_gene_example():
    trapi = {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {"ids": ["MONDO:0005151"], "categories": ["biolink:Disease"]},
                    "n1": {"categories": ["biolink:Gene"]}
                },
                "edges": {
                    "e0": {
                        "subject": "n1",
                        "object": "n0",
                        "predicates": ["biolink:gene_associated_with_condition"]
                    }
                }
            }
        }
    }

    return await monarch_get_associations(
        subject=None,
        object="MONDO:0005151",
        category="biolink:GeneToDiseaseAssociation"
    )
```

---

## Part C: ADK YAML Configuration

Ready-to-run ADK YAML for the epilepsy use case:

```yaml
name: epilepsy-multi-kg
version: 1.0

agents:
  - id: chatfront
    type: llm
    entrypoint: agents.chatfront_agent:ChatAgent

  - id: query_graph_builder
    type: llm
    entrypoint: agents.query_graph_builder_agent:QueryGraphBuilderAgent
    prompt_template: query_graph_builder_prompt

  - id: orchestrator
    type: llm
    entrypoint: agents.orchestrator_agent:OrchestratorAgent
    tools:
      - monarch
      - clinical_connections
      - biggim
      - drug_approvals
      - clinical_trials
      - wellness_multiomics
    prompt_template: orchestrator_prompt

  - id: evidence_merger
    type: code
    entrypoint: agents.evidence_merger_agent:merge_evidence

  - id: summariser
    type: llm
    entrypoint: agents.explanation_agent:ExplanationAgent
    prompt_template: explanation_prompt

tools:
  - id: monarch
    type: code
    entrypoint: tools.monarch_tool:monarch_get_associations

  - id: clinical_connections
    type: code
    entrypoint: tools.translator_kp_tool:TranslatorKPClient
    init_args:
      base_url: "https://smart-api.clinicalconnections/trapi/query"

  - id: biggim
    type: code
    entrypoint: tools.translator_kp_tool:TranslatorKPClient
    init_args:
      base_url: "https://biggim.org/trapi/query"

  - id: drug_approvals
    type: code
    entrypoint: tools.translator_kp_tool:TranslatorKPClient
    init_args:
      base_url: "https://drug-approvals.org/trapi/query"

  - id: clinical_trials
    type: code
    entrypoint: tools.translator_kp_tool:TranslatorKPClient
    init_args:
      base_url: "https://clinical-trials.org/trapi/query"

  - id: wellness_multiomics
    type: code
    entrypoint: tools.translator_kp_tool:TranslatorKPClient
    init_args:
      base_url: "https://multiomics-smart-api/trapi/query"

workflow:
  steps:
    - id: qgraph
      agent: query_graph_builder
      input_from: chatfront
      output_key: trapi_msg

    - id: fan_out
      agent: orchestrator
      input:
        trapi_message: "{{ steps.qgraph.output.trapi_msg }}"
      output_key: kg_responses

    - id: merge
      agent: evidence_merger
      input:
        responses: "{{ steps.fan_out.output.responses }}"
      output_key: merged_kg

    - id: explain
      agent: summariser
      input:
        question: "{{ chatfront.latest_user_message }}"
        evidence: "{{ steps.merge.output }}"
      output_key: final_answer

  return:
    from_step: explain
    key: final_answer
```

---

## Part D: Prompt Templates

### D.1 Query Graph Builder Prompt

```
You convert biomedical natural-language questions into TRAPI query graphs.
Use MONDO for disease, HGNC/NCBIGene for genes, ChEBI/DrugBank/RxCUI for drugs.
Output ONLY a JSON { "message": { "query_graph": ... } }.
```

### D.2 Orchestrator Prompt

```
You inspect TRAPI query_graph and decide which KGs to call:
- Monarch for disease-gene evidence
- ClinicalConnections for mechanistic gene-drug-disease paths
- BigGIM for expression/omics/drug response
- DrugApprovals for FDA-approved indications
- ClinicalTrials for ongoing trials
- Wellness Multiomics for pathway/variant insights

Output a JSON with "kg_calls" and "responses".
```

### D.3 Explanation Agent Prompt

```
You convert merged graph evidence into a structured answer:
1. High-level summary
2. Disease biology
3. Genes involved
4. Approved drugs
5. Investigational drugs
6. Clinical trial signals
7. Evidence provenance (KGs used)

Write like a clinical knowledge assistant.
```

---

## Part E: Workflow Diagrams

### E.1 UI Flow Diagram

```mermaid
flowchart TD

    subgraph UI[" User Interface (Chat App / Web App)"]
        U[User enters<br/>biomedical question]
        CF[Chatfront Agent<br/>(UI-facing LLM)]
        OUT[Assistant Response<br/>(Consolidated KM Answer)]
    end

    subgraph QG[" Query Understanding"]
        QGA[Query Graph Builder Agent]
        TRAPI[TRAPI Query Graph<br/>(message.query_graph)]
    end

    subgraph ORCH[" Multi-KG Orchestration Layer"]
        ORA[Orchestrator Agent]
    end

    subgraph KGAGENTS[" Knowledge Provider Agents"]
        MON[Monarch KG Agent]
        CC[Clinical Connections KG Agent]
        BG[BigGIM Drug Response Agent]
        DA[Drug Approvals Agent]
        CT[Clinical Trials Agent]
        OM[Multiomics Agent]
    end

    subgraph MERGE[" Evidence Normalisation & Fusion"]
        MER[Evidence Merger Agent]
    end

    subgraph EXP[" Explanation Layer"]
        EXA[Explanation Agent<br/>(LLM Summariser)]
    end

    %% Flows
    U --> CF
    CF --> QGA
    QGA --> TRAPI
    TRAPI --> ORA

    ORA --> MON
    ORA --> CC
    ORA --> BG
    ORA --> DA
    ORA --> CT
    ORA --> OM

    MON --> MER
    CC --> MER
    BG --> MER
    DA --> MER
    CT --> MER
    OM --> MER

    MER --> EXA
    EXA --> CF
    CF --> OUT
```

### E.2 Sequence Diagram

Representation of actual multi-agent invocation:

````mermaid
sequenceDiagram
    autonumber

    participant User
    participant CF as Chatfront Agent<br/>(LLM)
    participant QG as Query Graph Builder Agent<br/>(LLM)
    participant ORC as Orchestrator Agent<br/>(LLM)
    participant MON as Monarch KG Agent<br/>(Tool)
    participant CC as Clinical Connections KP<br/>(TRAPI Tool)
    participant BG as BigGIM KP<br/>(TRAPI Tool)
    participant DA as Drug Approvals KP<br/>(TRAPI Tool)
    participant CT as Clinical Trials KP<br/>(TRAPI Tool)
    participant OM as Multiomics KP<br/>(TRAPI Tool)
    participant MER as Evidence Merger Agent<br/>(Python)
    participant EXP as Explanation Agent<br/>(LLM)

    User->>CF: "What causes epilepsy and what drugs treat it?"
    CF->>QG: Passes cleaned query text
    QG->>QG: Build TRAPI Query Graph
    QG-->>CF: TRAPI Query Graph JSON
    CF->>ORC: Send query_graph

    %% Orchestration fan-out
    ORC->>MON: disease→gene association request
    MON-->>ORC: Monarch response

    ORC->>CC: TRAPI query (disease-gene-drug path)
    CC-->>ORC: ClinicalConnections response

    ORC->>BG: TRAPI query (drug–gene response profiles)
    BG-->>ORC: BigGIM response

    ORC->>DA: TRAPI query (drug approvals)
    DA-->>ORC: DrugApprovals response

    ORC->>CT: TRAPI query (disease–drug trials)
    CT-->>ORC: ClinicalTrials response

    ORC->>OM: TRAPI query (variants, pathways)
    OM-->>ORC: Multiomics response

    ORC-->>MER: All KG responses

    MER->>MER: Node/edge canonicalisation<br/>deduplication<br/>score aggregation
    MER-->>EXP: Merged evidence graph

    EXP->>EXP: Distil biomedical findings into text
    EXP-->>CF: Final answer narrative
    CF-->>User: "Epilepsy is linked to SCN1A… Valproate treats… Trials include…"
    
```

---

