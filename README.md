# Multi-KG BioAgent Chatbot

A **multi-agent, multi-knowledge-graph biomedical question–answering system** built with **Google ADK** and **TRAPI/ReasonerAPI**.

This project lets a user ask questions like:

> *“What causes epilepsy, which genes are involved, what drugs target those genes, and are there clinical trials?”*

The system:
1. Converts the question into a **ReasonerAPI / TRAPI query graph**.
2. Uses a **multi-agent orchestration layer** to query multiple biomedical **knowledge graphs (KGs)**:
   - Monarch Initiative KG
   - Clinical Connections KG
   - BigGIM Drug Response KG
   - Clinical Trials KG
   - Drug Approvals KG
   - Wellness Multiomics KG
3. **Merges and ranks evidence** across KGs.
4. Uses an LLM to generate a **consolidated, provenance-aware explanation**.

---

<img width="1024" height="412" alt="image" src="https://github.com/user-attachments/assets/66344dd4-3ebe-41d0-ad62-2f557934f15c" />

---

## Problem: Fragmented Biomedical Knowledge

Biomedical facts are scattered across many specialized KGs and APIs. No single source can fully answer multi-hop questions that span:

- Disease → Gene → Drug → Clinical Trial
- Disease → Phenotype → Gene → Pathway
- Gene → Variant → Drug Response

Clinicians and researchers must manually jump between portals and APIs, which is:

- **Time-consuming**
- **Error-prone**
- **Hard to reproduce**
- Difficult to explain or share as a single coherent answer

LLMs can explain, but **LLMs alone hallucinate** if not grounded in structured, curated knowledge.

---

##  What This Project Does

This project builds a **KG-aware chat assistant** that:

- Accepts **natural language biomedical questions**.
- Generates a **TRAPI query graph** using ReasonerAPI conventions.
- Queries **multiple KGs in parallel** via agents/tools:
  - Monarch Initiative (disease–gene–phenotype)
  - Clinical Connections (causal gene–drug–disease relationships)
  - BigGIM (expression / omics / drug response)
  - Drug Approvals KG (FDA labels)
  - Clinical Trials KG (NCT trials)
  - Wellness Multiomics KG (pathways, variants, omics)
- **Merges and ranks evidence** into a canonical mini-KG slice.
- Produces a **clear, explainable answer** with provenance information.

---

##  High-Level Architecture

<img width="1024" height="765" alt="image" src="https://github.com/user-attachments/assets/3597b831-2440-4bf9-a194-5ac2bac30a80" />
