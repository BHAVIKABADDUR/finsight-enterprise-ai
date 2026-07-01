# output/main_app.py
# FinSight Enterprise AI — Streamlit Frontend
# Run with: streamlit run output/main_app.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import json
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

# ── Load Streamlit secrets into environment (cloud deployment) ────────────────
try:
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    pass
load_dotenv()

st.set_page_config(
    page_title="FinSight Enterprise AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True
)

st.markdown("""<style>

:root {
    --ink: #0B0E14;
    --ink-soft: #3A3F4B;
    --ink-faint: #6B7280;
    --paper: #F7F5F0;
    --paper-raised: #FFFFFF;
    --hairline: #DDD8CC;
    --signal-red: #C8442C;
    --signal-red-bg: #FBEAE6;
    --verified-green: #2D5C4A;
    --verified-green-bg: #E8EFEC;
    --amber: #B07A1E;
    --amber-bg: #FBF1DE;
    --gold-accent: #B08D57;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}
.block-container {
    padding-top: 1.5rem !important;
    max-width: 1180px;
}

.stApp {
    background-color: var(--paper);
}

section[data-testid="stSidebar"] {
    background-color: var(--ink);
    border-right: 1px solid var(--hairline);
}
section[data-testid="stSidebar"] > div {
    padding-top: 0;
}
section[data-testid="stSidebar"] * {
    color: #E8E6DF !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12) !important;
    margin: 1rem 0 !important;
}
section[data-testid="stSidebar"] label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8B8F99 !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    border-radius: 2px;
    padding: 9px 10px !important;
    margin-bottom: 2px;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.01em;
    transition: background-color 0.15s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
    background-color: var(--signal-red);
}

.brand-mark {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    color: #F2F0EA !important;
    padding: 4px 0 0 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.brand-mark .dot {
    width: 8px;
    height: 8px;
    background: var(--signal-red);
    display: inline-block;
    border-radius: 50%;
}
.brand-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #8B8F99 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 2px;
}
.sidebar-stack-pill {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.04em;
    color: #B0AEA6 !important;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 2px;
    padding: 3px 7px;
    margin: 2px 4px 2px 0;
}

h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    color: var(--ink) !important;
    letter-spacing: -0.01em;
}
h1 {
    font-weight: 700 !important;
    font-size: 1.9rem !important;
    border-bottom: 3px solid var(--ink);
    padding-bottom: 0.5rem;
    margin-bottom: 0.3rem !important;
}
h2 { font-weight: 600 !important; font-size: 1.25rem !important; }
h3 { font-weight: 600 !important; font-size: 1.05rem !important; }

.page-kicker {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--gold-accent);
    margin-bottom: 2px;
    font-weight: 600;
}
.page-subtitle {
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--ink-faint);
    font-size: 0.92rem;
    margin-top: 0.4rem;
    margin-bottom: 1.2rem;
}

[data-testid="stMetric"] {
    background-color: var(--paper-raised);
    border: 1px solid var(--hairline);
    border-left: 3px solid var(--gold-accent);
    padding: 14px 16px;
    border-radius: 3px;
    box-shadow: 0 1px 2px rgba(11,14,20,0.04);
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 700 !important;
    color: var(--ink) !important;
    font-size: 1.5rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    text-transform: uppercase;
    font-size: 0.68rem !important;
    letter-spacing: 0.07em;
    color: var(--ink-faint) !important;
}

..stButton button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    border-radius: 2px !important;
    border: 1.5px solid var(--ink) !important;
    letter-spacing: 0.02em;
    font-size: 0.85rem !important;
    position: relative;
    z-index: 1;
}
}
.stButton button[kind="primary"] {
    background-color: var(--ink) !important;
    border-color: var(--ink) !important;
    color: #F7F5F0 !important;
}
.stButton button[kind="primary"]:hover {
    background-color: var(--signal-red) !important;
    border-color: var(--signal-red) !important;
}
.stButton button:not([kind="primary"]) {
    background-color: var(--paper-raised) !important;
    color: var(--ink) !important;
}
.stButton button:not([kind="primary"]):hover {
    border-color: var(--gold-accent) !important;
    color: var(--gold-accent) !important;
    background-color: var(--paper) !important;
}
.stDownloadButton button {
    font-family: 'IBM Plex Mono', monospace !important;
    border-radius: 2px !important;
    border: 1.5px solid var(--verified-green) !important;
    color: var(--verified-green) !important;
    background: var(--verified-green-bg) !important;
    font-weight: 600 !important;
}

div[data-testid="stAlert"] {
    border-radius: 3px !important;
    border-left-width: 4px !important;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.92rem;
}

button[data-baseweb="tab"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    font-size: 0.78rem !important;
    letter-spacing: 0.05em;
    color: var(--ink-faint) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--ink) !important;
}
div[data-baseweb="tab-highlight"] {
    background-color: var(--signal-red) !important;
}
div[data-baseweb="tab-border"] {
    background-color: var(--hairline) !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--hairline);
    border-radius: 3px;
}

details {
    border: 1px solid var(--hairline) !important;
    border-radius: 3px !important;
    background-color: var(--paper-raised) !important;
    margin-bottom: 6px;
}
summary {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
}

hr {
    border-color: var(--hairline) !important;
    margin: 1.1rem 0 !important;
}

.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    border-radius: 3px !important;
    border-color: var(--hairline) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--gold-accent) !important;
    box-shadow: 0 0 0 1px var(--gold-accent) !important;
}

code {
    font-family: 'IBM Plex Mono', monospace !important;
    background-color: var(--ink) !important;
    color: #E8E6DF !important;
    border-radius: 2px;
}

.risk-stamp {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 6px 14px;
    border-radius: 2px;
    border: 1.5px solid currentColor;
}
.risk-stamp.high { color: var(--signal-red); background: var(--signal-red-bg); }
.risk-stamp.medium { color: var(--amber); background: var(--amber-bg); }
.risk-stamp.low { color: var(--verified-green); background: var(--verified-green-bg); }

.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-faint);
    border-bottom: 1px solid var(--hairline);
    padding-bottom: 6px;
    margin-bottom: 10px;
    margin-top: 4px;
}

.app-footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--hairline);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--ink-faint);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

</style>
""", unsafe_allow_html=True)


def risk_stamp(level: str) -> str:
    level = (level or "unknown").lower()
    cls = "medium"
    icon = "●"
    if level == "high":
        cls, icon = "high", "▲"
    elif level == "low":
        cls, icon = "low", "✓"
    return f'<span class="risk-stamp {cls}">{icon} {level.upper()} RISK</span>'

def status_chip(label: str, kind: str = "neutral") -> str:
    """Render a small status chip — used for system health and pipeline status."""
    return f'<span class="status-chip {kind}">{label}</span>'


def empty_state(title: str, body: str) -> str:
    """Render a styled empty state box instead of plain st.info text."""
    return (
        f'<div class="empty-state">'
        f'<div class="empty-state-title">{title}</div>'
        f'<div>{body}</div>'
        f'</div>'
    )


def render_footer():
    """Render the app footer — call once at the bottom of every page."""
    st.markdown(
        '<div class="app-footer">'
        'FinSight Enterprise AI · LangGraph · MCP · Supabase · Groq · LLMOps · Build 2026.06'
        '</div>',
        unsafe_allow_html=True
    )
@st.cache_resource
def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

st.sidebar.markdown(
    '<div class="brand-mark"><span class="dot"></span>FINSIGHT</div>'
    '<div class="brand-sub">Enterprise AI · Risk Ledger</div>',
    unsafe_allow_html=True
)
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    ["🏠 Analysis", "📊 Dashboard", "📈 Trend Comparison", "🚩 Review Queue", "📋 Audit Log", "⚙️ System Health"],
    label_visibility="visible"
)

st.sidebar.divider()
st.sidebar.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;color:#8B8F99;margin-bottom:6px;">Stack</div>', unsafe_allow_html=True)
st.sidebar.markdown(
    '<span class="sidebar-stack-pill">LangGraph</span>'
    '<span class="sidebar-stack-pill">MCP</span>'
    '<span class="sidebar-stack-pill">n8n</span>'
    '<span class="sidebar-stack-pill">Supabase</span>'
    '<span class="sidebar-stack-pill">Qdrant</span>'
    '<span class="sidebar-stack-pill">Groq</span>'
    '<span class="sidebar-stack-pill">Streamlit</span>',
    unsafe_allow_html=True
)

if page == "🏠 Analysis":
    st.markdown('<div class="page-kicker">Multi-Agent Intelligence</div>', unsafe_allow_html=True)
    st.title("FinSight Enterprise AI")
    st.markdown('<div class="page-subtitle">Financial document analysis powered by a 5-agent LangGraph orchestration system</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["QUERY ANALYSIS", "UPLOAD DOCUMENT", "SQL SEARCH"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_area(
                "Enter your financial analysis query",
                value=st.session_state.get("query_input", ""),
                placeholder="e.g. Analyse our transactions and identify any suspicious activity...",
                height=100
            )
        with col2:
            st.markdown('<div class="section-label">Quick Queries</div>', unsafe_allow_html=True)
            if st.button("Check anomalies", use_container_width=True):
                st.session_state["query_input"] = "Identify all suspicious transactions and anomalies that need immediate review"
                st.rerun()
            if st.button("Spending summary", use_container_width=True):
                st.session_state["query_input"] = "Give me a complete summary of our spending patterns and trends"
                st.rerun()
            if st.button("High risk items", use_container_width=True):
                st.session_state["query_input"] = "What are the highest risk transactions in our financial data?"
                st.rerun()

        st.divider()

        if st.button("Run Analysis", type="primary", use_container_width=True):
            if not query:
                st.error("Enter a query before running analysis.")
            else:
                with st.spinner("Agents analysing financial data..."):
                    try:
                        from agents.graph import run_analysis
                        result = run_analysis(query)
                        st.session_state["last_analysis_result"] = result
                        st.session_state["last_analysis_query"] = query

                        decision = result.get("final_decision", {})
                        analysis = result.get("analysis_results", {})
                        extracted = result.get("extracted_data", {})

                        risk = decision.get("overall_risk_rating", "UNKNOWN")
                        st.markdown(risk_stamp(risk), unsafe_allow_html=True)

                        st.divider()

                        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
                        st.info(decision.get("executive_summary", "No summary available"))

                        st.markdown('<div class="section-label">Key Metrics</div>', unsafe_allow_html=True)
                        txn_summary = extracted.get("transactions", {}).get("summary", {})

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Transactions", txn_summary.get("total_transactions", txn_summary.get("total_count", 0)))
                        col2.metric("Total Credit", f"AED {txn_summary.get('total_credit_aed', 0):,.0f}")
                        col3.metric("Total Debit", f"AED {txn_summary.get('total_debit_aed', 0):,.0f}")
                        col4.metric("Flagged", txn_summary.get("flagged_count", 0), delta="Needs Review", delta_color="inverse")

                        st.divider()

                        st.markdown('<div class="section-label">Recommended Actions</div>', unsafe_allow_html=True)
                        actions = decision.get("recommended_actions", [])
                        for action in actions:
                            priority = action.get("priority", "monitor").upper()
                            if priority == "IMMEDIATE":
                                st.error(f"**{priority}** — {action.get('action', '')}")
                            elif priority == "SOON":
                                st.warning(f"**{priority}** — {action.get('action', '')}")
                            else:
                                st.info(f"**{priority}** — {action.get('action', '')}")

                        st.divider()

                        st.markdown('<div class="section-label">Primary Concerns</div>', unsafe_allow_html=True)
                        for concern in decision.get("primary_concerns", []):
                            st.markdown(f"— {concern}")

                        if decision.get("requires_human_review"):
                            st.divider()
                            st.warning(f"**Human review required** — {decision.get('human_review_reason', '')}")
                            st.caption("Open Review Queue to approve or reject flagged items.")

                        st.caption(f"Run ID: {result.get('run_id', 'N/A')}")

                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        st.exception(e)

        if "last_analysis_result" in st.session_state:
            st.divider()
            if st.button("Export PDF Report", use_container_width=True, key="export_query_report"):
                with st.spinner("Generating PDF report..."):
                    from llmops.report_generator import generate_analysis_report
                    stored_result = st.session_state["last_analysis_result"]
                    report_path = generate_analysis_report(
                        decision=stored_result.get("final_decision", {}),
                        analysis=stored_result.get("analysis_results", {}),
                        extracted=stored_result.get("extracted_data", {}),
                        query=st.session_state.get("last_analysis_query", ""),
                        run_id=stored_result.get("run_id", "unknown")
                    )

                    with open(report_path, "rb") as f:
                        st.download_button(
                            label="Download Report",
                            data=f,
                            file_name=os.path.basename(report_path),
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_query_report"
                        )
                    st.success("Report generated successfully.")

    with tab2:
        st.markdown('<div class="section-label">Document Upload</div>', unsafe_allow_html=True)
        st.markdown("Upload a bank statement or invoice PDF — agents extract and analyse it automatically.")
        st.divider()

        uploaded_file = st.file_uploader(
            "Drop your document here",
            type=["pdf", "csv"],
            help="Supported: Bank statements (PDF), Invoices (PDF), Transaction exports (CSV)"
        )

        if uploaded_file is not None:
            st.success(f"File received — {uploaded_file.name} ({uploaded_file.size:,} bytes)")

            col1, col2 = st.columns(2)
            with col1:
                doc_type = st.selectbox(
                    "Document type",
                    ["bank_statement", "invoice", "transaction_csv"],
                    help="Select what type of document this is"
                )
            with col2:
                st.markdown('<div class="section-label">File Details</div>', unsafe_allow_html=True)
                st.caption(f"Name — {uploaded_file.name}")
                st.caption(f"Type — {uploaded_file.type}")
                st.caption(f"Size — {uploaded_file.size:,} bytes")

            st.divider()

            if st.button("Extract & Analyse Document", type="primary", use_container_width=True):
                with st.spinner("Processing document through IDP pipeline..."):
                    try:
                        import tempfile
                        from pathlib import Path

                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=Path(uploaded_file.name).suffix
                        ) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name

                        st.info("Step 1/4 — Running OCR extraction")

                        if uploaded_file.name.endswith(".pdf"):
                            from extraction.ocr import extract_text_from_pdf
                            ocr_text = extract_text_from_pdf(tmp_path)
                            st.success(f"OCR complete — {len(ocr_text)} characters extracted")
                        else:
                            with open(tmp_path, "r", encoding="utf-8") as f:
                                ocr_text = f.read()
                            st.success(f"CSV loaded — {len(ocr_text)} characters")

                        with st.expander("Raw extracted text (first 500 chars)"):
                            st.text(ocr_text[:500])

                        st.info("Step 2/4 — Running LLM extraction")

                        from extraction.llm_extractor import extract_with_llm, validate_extraction
                        llm_result = extract_with_llm(ocr_text, doc_type)
                        validated, confidence = validate_extraction(
                            llm_result["extracted_fields"], doc_type
                        )

                        st.success(
                            f"LLM extraction complete — "
                            f"{confidence:.0%} confidence, "
                            f"{llm_result['tokens_used']} tokens, "
                            f"{llm_result['extraction_time_ms']}ms"
                        )

                        st.markdown('<div class="section-label">Extracted Fields</div>', unsafe_allow_html=True)
                        col_a, col_b = st.columns(2)
                        fields = validated
                        field_items = list(fields.items())
                        mid = len(field_items) // 2

                        with col_a:
                            for key, val in field_items[:mid]:
                                if val and key != "transactions":
                                    st.markdown(f"**{key.replace('_', ' ').title()}** — {val}")

                        with col_b:
                            for key, val in field_items[mid:]:
                                if val and key != "transactions":
                                    st.markdown(f"**{key.replace('_', ' ').title()}** — {val}")

                        transactions = fields.get("transactions", [])
                        if transactions:
                            st.markdown(f'<div class="section-label">Extracted Transactions ({len(transactions)})</div>', unsafe_allow_html=True)
                            import pandas as pd
                            df_txns = pd.DataFrame(transactions)
                            st.dataframe(df_txns, use_container_width=True)

                        st.divider()
                        st.info("Step 3/4 — Running agent analysis")

                        from agents.graph import run_analysis
                        query = (
                            f"Analyse this {doc_type.replace('_', ' ')} document. "
                            f"Extracted data: {str(validated)[:500]}. "
                            f"Identify any risks, anomalies or concerns."
                        )
                        result = run_analysis(query)
                        decision = result.get("final_decision", {})

                        st.info("Step 4/4 — Saving results")

                        import uuid as uuid_lib
                        doc_id = str(uuid_lib.uuid4())
                        supabase = get_supabase()
                        supabase.table("documents").insert({
                            "id": doc_id,
                            "file_name": uploaded_file.name,
                            "file_type": doc_type,
                            "status": "extracted",
                            "processed_at": datetime.utcnow().isoformat(),
                            "metadata": {
                                "confidence": confidence,
                                "tokens_used": llm_result["tokens_used"],
                                "source": "streamlit_upload"
                            }
                        }).execute()

                        st.divider()

                        risk = decision.get("overall_risk_rating", "UNKNOWN")
                        st.markdown(risk_stamp(risk), unsafe_allow_html=True)

                        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
                        st.info(decision.get("executive_summary", "No summary available"))

                        st.markdown('<div class="section-label">Recommended Actions</div>', unsafe_allow_html=True)
                        for action in decision.get("recommended_actions", []):
                            priority = action.get("priority", "monitor").upper()
                            if priority == "IMMEDIATE":
                                st.error(f"**{priority}** — {action.get('action', '')}")
                            elif priority == "SOON":
                                st.warning(f"**{priority}** — {action.get('action', '')}")
                            else:
                                st.info(f"**{priority}** — {action.get('action', '')}")

                        st.caption(f"Document fully processed. Document ID: {doc_id[:8]}…")

                        st.divider()
                        if st.button("Export PDF Report", use_container_width=True, key="export_upload_report"):
                            with st.spinner("Generating PDF report..."):
                                from llmops.report_generator import generate_analysis_report
                                report_path = generate_analysis_report(
                                    decision=decision,
                                    analysis=result.get("analysis_results", {}),
                                    extracted=result.get("extracted_data", {}),
                                    query=query,
                                    run_id=result.get("run_id", "unknown")
                                )

                                with open(report_path, "rb") as f:
                                    st.download_button(
                                        label="Download Report",
                                        data=f,
                                        file_name=os.path.basename(report_path),
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key="download_upload_report"
                                    )
                                st.success("Report generated successfully.")

                        os.unlink(tmp_path)

                    except Exception as e:
                        st.error(f"Processing failed: {str(e)}")
                        st.exception(e)

    with tab3:
        st.markdown('<div class="section-label">Natural Language Transaction Search</div>', unsafe_allow_html=True)
        st.markdown("Ask questions in plain English — an AI agent converts it into a safe database query.")
        st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            sql_query = st.text_input(
                "Ask a question",
                value=st.session_state.get("sql_query_input", ""),
                placeholder="e.g. Show me all transactions over AED 10,000"
            )
        with col2:
            st.markdown('<div class="section-label">Try These</div>', unsafe_allow_html=True)
            if st.button("Large transactions", use_container_width=True):
                st.session_state["sql_query_input"] = "Show me all transactions over AED 10,000"
                st.rerun()
            if st.button("Flagged items", use_container_width=True):
                st.session_state["sql_query_input"] = "What flagged transactions do we have?"
                st.rerun()
            if st.button("Salary payments", use_container_width=True):
                st.session_state["sql_query_input"] = "Show me all salary transactions"
                st.rerun()

        st.divider()

        if st.button("Search", type="primary", use_container_width=True):
            if not sql_query:
                st.error("Enter a question before searching.")
            else:
                with st.spinner("Converting your question into a safe query..."):
                    try:
                        from agents.sql_agent import query_with_natural_language
                        result = query_with_natural_language(sql_query)

                        st.success(result['explanation'])

                        with st.expander("Technical details — filters applied"):
                            for f in result["applied_filters"]:
                                st.code(f, language="sql")

                        st.caption(f"{result['result_count']} results found")

                        if result["results"]:
                            import pandas as pd
                            df_results = pd.DataFrame(result["results"])

                            display_cols = [
                                "transaction_date", "description", "amount",
                                "transaction_type", "category", "is_flagged"
                            ]
                            display_cols = [c for c in display_cols if c in df_results.columns]

                            df_display = df_results[display_cols].rename(columns={
                                "transaction_date": "Date",
                                "description": "Description",
                                "amount": "Amount (AED)",
                                "transaction_type": "Type",
                                "category": "Category",
                                "is_flagged": "Flagged"
                            })

                            st.dataframe(df_display, use_container_width=True)
                        else:
                            st.info("No matching transactions found.")

                    except Exception as e:
                        st.error(f"Search failed: {str(e)}")
                        st.exception(e)

elif page == "📊 Dashboard":
    st.markdown('<div class="page-kicker">Gold Layer</div>', unsafe_allow_html=True)
    st.title("Financial Intelligence Dashboard")
    st.markdown('<div class="page-subtitle">KPIs updated after every pipeline run</div>', unsafe_allow_html=True)

    supabase = get_supabase()

    st.markdown('<div class="section-label">Spend by Category</div>', unsafe_allow_html=True)
    try:
        result = supabase.table("gold_spend_by_category").select("*").order(
            "total_amount", desc=True
        ).execute()
        categories = result.data

        if categories:
            import plotly.express as px
            import pandas as pd

            df = pd.DataFrame(categories)
            fig = px.bar(
                df, x="category", y="total_amount", color="total_amount",
                color_continuous_scale=["#E8E2D4", "#0B0E14"],
                labels={"total_amount": "Amount (AED)", "category": "Category"}
            )
            fig.update_layout(
                showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="IBM Plex Mono", margin=dict(t=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[["category", "total_amount", "transaction_count", "avg_amount"]].rename(
                    columns={
                        "category": "Category", "total_amount": "Total (AED)",
                        "transaction_count": "Count", "avg_amount": "Average (AED)"
                    }
                ),
                use_container_width=True
            )
        
        else:
            st.markdown(empty_state("No Gold Layer Data", "Run the ETL pipeline to populate dashboard metrics."), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading categories: {e}")

    st.divider()

    st.markdown('<div class="section-label">Monthly Trends</div>', unsafe_allow_html=True)
    try:
        result = supabase.table("gold_monthly_trends").select("*").execute()
        trends = result.data

        if trends:
            import plotly.express as px
            import pandas as pd
            df_trends = pd.DataFrame(trends)
            df_trends["period"] = df_trends["month"] + " " + df_trends["year"].astype(str)

            fig2 = px.line(
                df_trends, x="period", y=["total_credit", "total_debit"],
                labels={"value": "Amount (AED)", "period": "Month"},
                color_discrete_map={"total_credit": "#2D5C4A", "total_debit": "#C8442C"}
            )
            fig2.update_traces(line_width=3)
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="IBM Plex Mono", margin=dict(t=10)
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No trend data yet.")
    except Exception as e:
        st.error(f"Error loading trends: {e}")

    st.divider()

    st.markdown('<div class="section-label">Flagged Transaction Summary</div>', unsafe_allow_html=True)
    try:
        result = supabase.table("gold_flagged_summary").select("*").execute()
        flagged = result.data

        if flagged:
            import plotly.express as px
            import pandas as pd
            df_flagged = pd.DataFrame(flagged)
            fig3 = px.pie(
                df_flagged, names="flag_reason_type", values="total_amount",
                color_discrete_sequence=["#C8442C", "#B08D57", "#3A3F4B"]
            )
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", font_family="IBM Plex Mono", margin=dict(t=10)
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No flagged transactions.")
    except Exception as e:
        st.error(f"Error loading flagged summary: {e}")

elif page == "📈 Trend Comparison":
    st.markdown('<div class="page-kicker">Multi-Period Analysis</div>', unsafe_allow_html=True)
    st.title("Trend Comparison")
    st.markdown('<div class="page-subtitle">AI-powered comparison of spending patterns and risk trajectory across months</div>', unsafe_allow_html=True)

    focus = st.text_input(
        "What should the comparison focus on?",
        value="spending patterns and risk trends across all months",
        help="e.g. 'Transfer category spending' or 'flagged transaction trends'"
    )

    if st.button("Run Comparison Analysis", type="primary", use_container_width=True):
        with st.spinner("Comparing periods and identifying trends..."):
            try:
                from agents.comparison_agent import compare_periods
                result = compare_periods(focus)
                comparison = result["comparison"]

                st.divider()

                risk_trajectory = comparison.get("risk_trajectory", "unknown").upper()
                traj_map = {"WORSENING": "high", "IMPROVING": "low"}
                st.markdown(risk_stamp(traj_map.get(risk_trajectory, "medium")), unsafe_allow_html=True)
                st.caption(f"Risk trajectory: {risk_trajectory}")

                st.markdown('<div class="section-label">Trend Summary</div>', unsafe_allow_html=True)
                st.info(comparison.get("trend_summary", "No summary available"))

                st.divider()

                st.markdown('<div class="section-label">Period-by-Period Breakdown</div>', unsafe_allow_html=True)
                period_comparisons = comparison.get("period_comparisons", [])

                if period_comparisons:
                    import pandas as pd
                    import plotly.express as px

                    df_periods = []
                    for p in period_comparisons:
                        spend = p.get("total_spend", 0)
                        try:
                            spend = float(spend)
                        except (ValueError, TypeError):
                            spend = 0.0
                        df_periods.append({
                            "Period": p.get("period", ""),
                            "Total Spend (AED)": spend,
                            "Change": p.get("change_from_previous", ""),
                            "Notable Change": p.get("notable_change", "")
                        })

                    df_periods = pd.DataFrame(df_periods)

                    fig = px.line(
                        df_periods, x="Period", y="Total Spend (AED)",
                        markers=True
                    )
                    fig.update_traces(line_color="#0B0E14", line_width=3, marker=dict(color="#C8442C", size=8))
                    fig.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_family="IBM Plex Mono", margin=dict(t=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    for p in period_comparisons:
                        spend = p.get("total_spend", 0)
                        try:
                            spend = float(spend)
                        except (ValueError, TypeError):
                            spend = 0.0
                        change_pct = p.get("change_percentage", 0)
                        try:
                            change_pct = float(change_pct)
                        except (ValueError, TypeError):
                            change_pct = 0.0

                        with st.expander(f"{p.get('period', '')} — AED {spend:,.2f} ({change_pct:+.1f}%)"):
                            st.markdown(f"**Change** — {p.get('change_from_previous', 'N/A')}")
                            st.markdown(f"**Notable** — {p.get('notable_change', '')}")

                st.divider()

                st.markdown('<div class="section-label">Category Shifts</div>', unsafe_allow_html=True)
                for shift in comparison.get("category_shifts", []):
                    trend = shift.get("trend", "stable")
                    if trend == "increasing":
                        st.warning(f"**{shift.get('category', '')}** ↑ — {shift.get('observation', '')}")
                    elif trend == "decreasing":
                        st.success(f"**{shift.get('category', '')}** ↓ — {shift.get('observation', '')}")
                    else:
                        st.info(f"**{shift.get('category', '')}** → — {shift.get('observation', '')}")

                st.divider()

                st.markdown('<div class="section-label">Key Insight</div>', unsafe_allow_html=True)
                st.success(comparison.get("key_insight", ""))

                st.markdown('<div class="section-label">Recommendation</div>', unsafe_allow_html=True)
                st.info(comparison.get("recommendation", ""))

            except Exception as e:
                st.error(f"Comparison failed: {str(e)}")
                st.exception(e)

elif page == "🚩 Review Queue":
    st.markdown('<div class="page-kicker">Human-in-the-Loop</div>', unsafe_allow_html=True)
    st.title("Review Queue")
    st.markdown('<div class="page-subtitle">Flagged transactions requiring human approval</div>', unsafe_allow_html=True)

    supabase = get_supabase()

    try:
        result = supabase.table("transactions").select("*").eq("is_flagged", True).execute()
        flagged_txns = result.data

        if not flagged_txns:
            st.success("No flagged transactions. All clear.")
        else:
            st.warning(f"{len(flagged_txns)} transactions require review")
            st.divider()

            for txn in flagged_txns:
                amount = float(txn.get("amount", 0))

                if amount > 75000:
                    badge_level = "high"
                elif amount > 20000:
                    badge_level = "medium"
                else:
                    badge_level = "low"

                with st.expander(
                    f"{txn.get('description', 'Unknown')} — "
                    f"AED {amount:,.2f} — {txn.get('transaction_date', '')}"
                ):
                    st.markdown(risk_stamp(badge_level), unsafe_allow_html=True)
                    st.markdown("")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Description** — {txn.get('description', '')}")
                        st.markdown(f"**Amount** — AED {amount:,.2f}")
                        st.markdown(f"**Type** — {txn.get('transaction_type', '').upper()}")
                        st.markdown(f"**Category** — {txn.get('category', '')}")
                    with col2:
                        st.markdown(f"**Date** — {txn.get('transaction_date', '')}")
                        st.markdown(f"**Flag Reason** — {txn.get('flag_reason', '')}")
                        st.markdown(f"**Currency** — {txn.get('currency', 'AED')}")

                    st.divider()
                    notes = st.text_input("Reviewer notes (optional)", key=f"notes_{txn['id']}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Approve", key=f"approve_{txn['id']}", use_container_width=True):
                            supabase.table("review_queue").insert({
                                "transaction_id": txn["id"],
                                "run_id": str(uuid.uuid4()),
                                "flag_reason": txn.get("flag_reason", ""),
                                "risk_level": "high" if amount > 75000 else "medium",
                                "status": "approved",
                                "reviewer_notes": notes,
                                "reviewed_at": datetime.utcnow().isoformat()
                            }).execute()
                            st.success("Transaction approved.")
                            st.rerun()

                    with col_b:
                        if st.button("Reject", key=f"reject_{txn['id']}", use_container_width=True):
                            supabase.table("review_queue").insert({
                                "transaction_id": txn["id"],
                                "run_id": str(uuid.uuid4()),
                                "flag_reason": txn.get("flag_reason", ""),
                                "risk_level": "high" if amount > 75000 else "medium",
                                "status": "rejected",
                                "reviewer_notes": notes,
                                "reviewed_at": datetime.utcnow().isoformat()
                            }).execute()
                            st.error("Transaction rejected.")
                            st.rerun()

    except Exception as e:
        st.error(f"Error loading review queue: {e}")

elif page == "📋 Audit Log":
    st.markdown('<div class="page-kicker">Governance Trail</div>', unsafe_allow_html=True)
    st.title("Audit Log")
    st.markdown('<div class="page-subtitle">Complete record of every agent decision</div>', unsafe_allow_html=True)

    supabase = get_supabase()

    try:
        result = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
        logs = result.data

        if not logs:
            st.info("No audit logs yet. Run an analysis first.")
        else:
            st.caption(f"Showing {len(logs)} most recent audit entries")
            st.divider()

            run_ids = list(dict.fromkeys([l["run_id"] for l in logs]))

            for run_id in run_ids[:5]:
                run_logs = [l for l in logs if l["run_id"] == run_id]
                first_log = run_logs[0]

                with st.expander(
                    f"Run {run_id[:8]}… — "
                    f"{first_log.get('created_at', '')[:19]} — "
                    f"{len(run_logs)} agent entries"
                ):
                    for log in run_logs:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"**{log.get('agent_name', '').upper()}**")
                            st.code(log.get('action', ''), language=None)
                        with col2:
                            st.markdown(f"**Decision** — {log.get('decision', '')}")
                            st.caption(log.get('reasoning', '')[:150])
                        st.divider()

        st.markdown('<div class="section-label">Run Metrics</div>', unsafe_allow_html=True)
        metrics_result = supabase.table("run_metrics").select("*").order("created_at", desc=True).limit(10).execute()
        metrics = metrics_result.data

        if metrics:
            import pandas as pd
            df_metrics = pd.DataFrame(metrics)
            st.dataframe(
                df_metrics[[
                    "run_id", "total_tokens", "total_cost_usd",
                    "transactions_extracted", "flags_raised", "status"
                ]].rename(columns={
                    "run_id": "Run ID", "total_tokens": "Tokens",
                    "total_cost_usd": "Cost (USD)", "transactions_extracted": "Transactions",
                    "flags_raised": "Flags", "status": "Status"
                }),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error loading audit log: {e}")

elif page == "⚙️ System Health":
    st.markdown('<div class="page-kicker">LLMOps Observability</div>', unsafe_allow_html=True)
    st.title("System Health")
    st.markdown('<div class="page-subtitle">Tokens, costs and agent performance across every run</div>', unsafe_allow_html=True)

    try:
        from llmops.dashboard import get_system_health, get_agent_performance

        health = get_system_health()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Documents", health["total_documents"])
        col2.metric("Transactions", health["total_transactions"])
        col3.metric("Flagged", health["flagged_transactions"], delta="Need Review", delta_color="inverse")
        col4.metric("Agent Runs", health["total_agent_runs"])

        st.divider()

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Tokens Used", f"{health['total_tokens_used']:,}")
        col6.metric("Cost (USD)", f"${health['total_cost_usd']:.4f}")
        col7.metric("Audit Entries", health["total_audit_entries"])
        col8.metric("Status", health["system_status"].upper(), delta="Online", delta_color="normal")
        st.markdown(status_chip("● HEALTHY", "healthy"), unsafe_allow_html=True)
        st.divider()

        st.markdown('<div class="section-label">Agent Performance</div>', unsafe_allow_html=True)
        perf = get_agent_performance()

        if perf:
            import pandas as pd
            df_perf = pd.DataFrame(perf)
            df_perf = df_perf[["agent_name", "total_calls"]].rename(columns={"agent_name": "Agent", "total_calls": "Total Calls"})
            st.dataframe(df_perf, use_container_width=True)

            import plotly.express as px
            fig = px.bar(
                df_perf, x="Agent", y="Total Calls", color="Total Calls",
                color_continuous_scale=["#E8E2D4", "#0B0E14"]
            )
            fig.update_layout(
                showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_family="IBM Plex Mono", margin=dict(t=10)
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.markdown('<div class="section-label">Pipeline Status</div>', unsafe_allow_html=True)
        supabase = get_supabase()
        docs_result = supabase.table("documents").select("*").execute()
        docs = docs_result.data

        if docs:
            import pandas as pd
            df_docs = pd.DataFrame(docs)
            st.dataframe(
                df_docs[["file_name", "file_type", "status", "uploaded_at"]].rename(
                    columns={"file_name": "File", "file_type": "Type", "status": "Status", "uploaded_at": "Uploaded"}
                ),
                use_container_width=True
            )

        st.divider()

        st.markdown('<div class="section-label">Extraction Results</div>', unsafe_allow_html=True)
        ext_result = supabase.table("extraction_results").select("*").execute()
        extractions = ext_result.data

        if extractions:
            for ext in extractions:
                doc_id = ext.get("document_id", "")[:8]
                model = ext.get("model_used", "")
                tokens = ext.get("tokens_used", 0)
                time_ms = ext.get("extraction_time_ms", 0)
                confidence = ext.get("confidence_scores", {})

                with st.expander(f"Document {doc_id}… — {model} — {tokens} tokens — {time_ms}ms"):
                    st.json(confidence)
                    fields = ext.get("extracted_fields", {})
                    st.json(fields)
        else:
            st.info("No extraction results yet. Run the extraction pipeline first.")

    except Exception as e:
        st.error(f"Error loading system health: {e}")
        st.exception(e)

render_footer()