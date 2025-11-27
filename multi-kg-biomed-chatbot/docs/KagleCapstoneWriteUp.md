**MultiKG-BioAgent: Multi-Knowledge Graph Querying with Google ADK & MCP**
**Agents Intensive Capstone Project - Phase 1**

### **Executive Summary**

This project introduces a **Multi-Agent System** designed to bridge the gap between natural language questions and structured **Biomedical Knowledge Graphs (KGs)**. By leveraging the **Google Agent Development Kit (ADK)** and the **Model Context Protocol (MCP)**, we have created an agent capable of translating simple clinical questions into standardized **TRAPI (Translator Reasoner API)** queries. These TRAPI queries are then submitted to multiple biomedical KGs to retrieve relevant, grounded information in the form of knowledge graph. An LLM them utilized the question, its TRAPI query, and associated response to generated grounded answers.

![Core-workflow](/multi-kg-biomed-chatbot/assets/MultiKGBioAgent-Dashboard.png)
Figure: MultiKG-BioAgent User Interface 


In this **Phase 1** implementation, the system focuses on **Diseases, Genes, and Chemical Entities**, solving the critical problem of "identifier hallucination" in LLMs by grounding every term using the **Ontology Lookup Service (OLS)** before querying.

### **The Problem**

Biomedical data is vast but siloed in complex graph databases (e.g., HetioNet, ROBOKOP). Querying these requires:

1.  **Expertise in query languages** (Cypher, SPARQL).
2.  **Knowledge of specific ontologies** (MONDO for diseases, HGNC for genes, CHEBI for chemicals).
3.  **Precise Identifiers (CURIEs):** An LLM might know "Tylenol," but the Knowledge Graph only understands CHEMBL:112 or PUBCHEM:1983.

Standard LLMs often "hallucinate" these IDs or generate syntactically incorrect graph queries, leading to zero results.

### **The Solution: Agent-Driven TRAPI Construction**

Our solution creates a deterministic pipeline where an AI Agent mediates the conversation between the user and the database.

Core Concept:

NLP Question ➡️ Ontology Grounding (OLS via MCP) ➡️ TRAPI Query Construction ➡️ Multi-KG Execution ➡️ Grounded Response

### **Key Innovations**

  * **Google ADK Framework:** Utilized for robust agent orchestration, state management, and tool routing.
  * **MCP for OLS:** We implement the **Model Context Protocol** to interface with the **Ontology Lookup Service (OLS)**. This treats the ontology search as a "tool" the agent can call to find the exact CURIE for a term (e.g., mapping "Breast Cancer" to MONDO:0005130).
  * **TRAPI Standard:** By generating queries in the standard TRAPI JSON format, our agent is backend-agnostic—it can query *any* TRAPI-compliant knowledge graph.

### **Architecture & Workflow**

The system is built on **Google Vertex AI Agent Builder** using the **ADK Python SDK**.

### **Step-by-Step Flow (Phase 1)**

1.  **User Query:** "What genes are associated with Type 2 Diabetes?"
2.  **Entity Extraction & Grounding:**
      * The Agent recognizes "Type 2 Diabetes" as a disease and "genes" as a target category.
      * **Tool Call (MCP):** `search_ontology(term="Type 2 Diabetes")`
      * **Result:** `MONDO:0005148`
3.  **TRAPI Construction:**
      * The agent constructs a TRAPI JSON object.
      * **Source Node:** `id: "MONDO:0005148"`
      * **Edge:** `predicates: ["biolink:condition_associated_with_gene"]`
      * **Target Node:** `categories: ["biolink:Gene"]`
4.  **Execution:** The TRAPI JSON is sent to the KG API.
5.  **Response:** The graph returns a list of genes (e.g., TCF7L2, KCNQ1). The agent summarizes these findings back to the user.

### **Technology Stack**

  * **Framework:** [Google Agent Development Kit (ADK)](https://github.com/google/adk-python)
  * **LLM:** Gemini 1.5 Pro (via Vertex AI)
  * **Protocol:** Model Context Protocol (MCP)
  * **Ontology Source:** EBI Ontology Lookup Service (OLS)
  * **Query Standard:** TRAPI (Translator Reasoner API) version 1.5
  * **Target Domain:** Diseases, Genes, Chemical Entities

### **Phase 1 Scope: "The Triad"**

As this is the initial phase of a long-term project, we have strictly scoped the agent to handle **1-2 sentence queries** focusing on the "Golden Triad" of biomedical entities:

1.  **Diseases:** Grounded to **MONDO** / **DOID**.
2.  **Genes:** Grounded to **HGNC** / **NCBIGene**.
3.  **Chemical Entities (Drugs):** Grounded to **CHEBI** / **CHEMBL**.

**Example Supported Queries:**

  * "Which drugs target the ACE2 gene?"
  * "Find diseases associated with high glucose."
  * "What is the chemical structure of Aspirin?"

### **Future Roadmap**

  * **Phase 2:** Multi-hop reasoning (e.g., "Find drugs that treat diseases associated with Gene X").
  * **Phase 3:** Integration of Clinical Trial Data KGs.
  * **Phase 4:** Autonomous hypothesis generation and validation loops.

### **Conclusion**

This capstone demonstrates that by combining **Google ADK's** orchestration capabilities with **MCP's** standardized tool interfaces, we can solve the "last mile" problem of interacting with complex scientific databases. We move beyond simple keyword search to true, semantically grounded knowledge retrieval.
