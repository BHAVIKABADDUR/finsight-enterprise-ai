# FinSight Enterprise AI

> A production-grade financial document intelligence platform built to mirror the enterprise AI systems being deployed across UAE banking and fintech in 2026.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-1a1a2e)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-C8442C)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E)
![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-orange)
![Tests](https://img.shields.io/badge/Tests-35%20passing-2D5C4A)
![License](https://img.shields.io/badge/License-MIT-B08D57)

---

## What this is

FinSight ingests financial documents — bank statements, invoices, transaction exports — and runs them through a complete AI pipeline: OCR extraction, LLM-based structuring, a 5-agent LangGraph orchestration system that analyses risk and anomalies, custom MCP tool servers that mediate every database interaction, an n8n automation layer, and a full governance trail with human-in-the-loop approval for high-risk decisions.

It was built end-to-end over several days as a portfolio project targeting AI Systems Engineer and Data Engineer roles in the UAE market, with every component chosen to mirror what real enterprise AI teams in banking are building right now — not a toy demo, a working system with 387 synthetic transactions across 3 business entities, full observability, and 35 passing tests.

## Live demo

| | |
|---|---|
| **App** | *[add your Streamlit Cloud link here after deployment]* |
| **Demo video** | *[add your 90-second walkthrough link here]* |
| **Repo** | https://github.com/BHAVIKABADDUR/finsight-enterprise-ai |

## Architecture

finsight-enterprise-ai/
├── ingestion/            Synthetic data generator, n8n workflow exports
├── pipeline/              Bronze → Silver → Gold data pipeline
├── extraction/            OCR, LLM extraction, Qdrant embeddings
├── mcp_servers/           4 custom MCP tool servers
├── agents/                LangGraph 5-agent system, SQL agent, comparison agent
├── hitl/                  Human-in-the-loop interrupt and review logic
├── llmops/                Cost tracking, evaluation, PDF report generation
├── output/                Streamlit application
├── database/              Supabase schema
├── tests/                 35 unit tests
└── config/                Environment and connection testing

## Running locally

**Prerequisites:** Python 3.11+, Tesseract OCR, Poppler, Docker (for n8n), free accounts on Supabase, Qdrant Cloud, Groq, and LangSmith.

```bash
git clone https://github.com/BHAVIKABADDUR/finsight-enterprise-ai.git
cd finsight-enterprise-ai
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API keys. Then run the database schema in Supabase's SQL Editor (`database/schema.sql`), generate synthetic data, and run the pipeline:

```bash
python ingestion/generate_synthetic_data.py
python -m pipeline.bronze
python -m pipeline.silver
python -m pipeline.gold
streamlit run output/main_app.py
```

## Testing

```bash
pytest tests/ -v
```

35 tests covering data cleaning, anomaly detection rules, SQL injection prevention, and HITL trigger logic.

## A note on data

All data in this project is synthetic, generated specifically for this system with realistic UAE financial patterns — company names, IBAN formats, AED amounts, and VAT calculations — with intentionally embedded anomalies (duplicate transactions, unusually large amounts, suspicious round numbers) for the agents to detect. No real financial data is used or stored, consistent with how enterprise AI teams handle development and testing in regulated industries.

## Author

Bhavika Baddur — Computer Science graduate, AI & Data Engineering background.
[LinkedIn](#) · [GitHub](https://github.com/BHAVIKABADDUR)

---

*Built as a demonstration of production-grade agentic AI system design, not a tutorial project. Every architectural decision — MCP over direct API calls, Medallion architecture over flat tables, HITL interrupts over silent automation — was made to mirror how this would actually be built for a bank.*