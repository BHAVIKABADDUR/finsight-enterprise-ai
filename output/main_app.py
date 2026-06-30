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

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight Enterprise AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Supabase client ───────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/bank.png", width=60)
st.sidebar.title("FinSight Enterprise AI")
st.sidebar.markdown("*Financial Document Intelligence*")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Analysis", "📊 Dashboard", "🚩 Review Queue", "📋 Audit Log", "⚙️ System Health"]
)

st.sidebar.divider()
st.sidebar.markdown("**Stack**")
st.sidebar.markdown("LangGraph · MCP · n8n")
st.sidebar.markdown("Supabase · Qdrant · Groq")
st.sidebar.markdown("Python 3.11 · Streamlit")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Analysis":
    st.title("🏦 FinSight Enterprise AI")
    st.markdown("*Intelligent Financial Document Analysis powered by LangGraph Agents*")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["💬 Query Analysis", "📄 Upload Document", "🔎 SQL Search"])

   # ── TAB 1: Query Analysis ─────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_area(
                "Enter your financial analysis query:",
                value=st.session_state.get("query_input", ""),
                placeholder="e.g. Analyse our transactions and identify any suspicious activity...",
                height=100
            )
        with col2:
            st.markdown("**Example queries:**")
            if st.button("🔍 Check anomalies", use_container_width=True):
                st.session_state["query_input"] = "Identify all suspicious transactions and anomalies that need immediate review"
                st.rerun()
            if st.button("📈 Spending summary", use_container_width=True):
                st.session_state["query_input"] = "Give me a complete summary of our spending patterns and trends"
                st.rerun()
            if st.button("⚠️ High risk items", use_container_width=True):
                st.session_state["query_input"] = "What are the highest risk transactions in our financial data?"
                st.rerun()

        st.divider()

        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            if not query:
                st.error("Please enter a query first")
            else:
                with st.spinner("🤖 Agents are analysing your financial data..."):
                    try:
                        from agents.graph import run_analysis
                        result = run_analysis(query)
                        st.session_state["last_analysis_result"] = result
                        st.session_state["last_analysis_query"] = query

                        decision = result.get("final_decision", {})
                        analysis = result.get("analysis_results", {})
                        extracted = result.get("extracted_data", {})

                        risk = decision.get("overall_risk_rating", "UNKNOWN")
                        if risk == "HIGH":
                            st.error(f"🔴 Risk Rating: {risk}")
                        elif risk == "MEDIUM":
                            st.warning(f"🟡 Risk Rating: {risk}")
                        else:
                            st.success(f"🟢 Risk Rating: {risk}")

                        st.divider()

                        st.subheader("📋 Executive Summary")
                        st.info(decision.get("executive_summary", "No summary available"))

                        st.subheader("📊 Key Metrics")
                        txn_summary = extracted.get("transactions", {}).get("summary", {})

                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Total Transactions", txn_summary.get("total_transactions", txn_summary.get("total_count", 0)))
                        col2.metric("Total Credit", f"AED {txn_summary.get('total_credit_aed', 0):,.0f}")
                        col3.metric("Total Debit", f"AED {txn_summary.get('total_debit_aed', 0):,.0f}")
                        col4.metric("Flagged", txn_summary.get("flagged_count", 0), delta="Needs Review", delta_color="inverse")

                        st.divider()

                        st.subheader("⚡ Recommended Actions")
                        actions = decision.get("recommended_actions", [])
                        for action in actions:
                            priority = action.get("priority", "monitor").upper()
                            if priority == "IMMEDIATE":
                                st.error(f"🔴 **{priority}**: {action.get('action', '')}")
                            elif priority == "SOON":
                                st.warning(f"🟡 **{priority}**: {action.get('action', '')}")
                            else:
                                st.info(f"🔵 **{priority}**: {action.get('action', '')}")

                        st.divider()

                        st.subheader("⚠️ Primary Concerns")
                        for concern in decision.get("primary_concerns", []):
                            st.markdown(f"• {concern}")

                        if decision.get("requires_human_review"):
                            st.divider()
                            st.warning(f"👤 **Human Review Required**: {decision.get('human_review_reason', '')}")
                            st.markdown("Go to **🚩 Review Queue** to approve or reject flagged items.")

                        st.success(f"✅ Analysis complete. Run ID: {result.get('run_id', 'N/A')}")

                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        st.exception(e)

        # ── Export Report Button (persists across reruns) ────────────────────
        if "last_analysis_result" in st.session_state:
            st.divider()
            if st.button("📄 Export PDF Report", use_container_width=True, key="export_query_report"):
                with st.spinner("Generating professional PDF report..."):
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
                            label="⬇️ Download Report",
                            data=f,
                            file_name=os.path.basename(report_path),
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_query_report"
                        )
                    st.success(f"✅ Report generated successfully")
                    
    # ── TAB 2: Upload Document ────────────────────────────────────────────────
    with tab2:
        st.subheader("📄 Upload Financial Document")
        st.markdown("Upload a bank statement or invoice PDF — agents will extract and analyse it automatically.")
        st.divider()

        uploaded_file = st.file_uploader(
            "Drop your document here",
            type=["pdf", "csv"],
            help="Supported: Bank statements (PDF), Invoices (PDF), Transaction exports (CSV)"
        )

        if uploaded_file is not None:
            st.success(f"✅ File received: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

            col1, col2 = st.columns(2)
            with col1:
                doc_type = st.selectbox(
                    "Document type:",
                    ["bank_statement", "invoice", "transaction_csv"],
                    help="Select what type of document this is"
                )
            with col2:
                st.markdown("**File details:**")
                st.markdown(f"Name: `{uploaded_file.name}`")
                st.markdown(f"Type: `{uploaded_file.type}`")
                st.markdown(f"Size: `{uploaded_file.size:,} bytes`")

            st.divider()

            if st.button("🔬 Extract & Analyse Document", type="primary", use_container_width=True):
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

                        st.info("📖 Step 1/4: Running OCR extraction...")

                        if uploaded_file.name.endswith(".pdf"):
                            from extraction.ocr import extract_text_from_pdf
                            ocr_text = extract_text_from_pdf(tmp_path)
                            st.success(f"✅ OCR complete: {len(ocr_text)} characters extracted")
                        else:
                            with open(tmp_path, "r", encoding="utf-8") as f:
                                ocr_text = f.read()
                            st.success(f"✅ CSV loaded: {len(ocr_text)} characters")

                        with st.expander("📝 Raw extracted text (first 500 chars)"):
                            st.text(ocr_text[:500])

                        st.info("🤖 Step 2/4: Running LLM extraction...")

                        from extraction.llm_extractor import extract_with_llm, validate_extraction
                        llm_result = extract_with_llm(ocr_text, doc_type)
                        validated, confidence = validate_extraction(
                            llm_result["extracted_fields"], doc_type
                        )

                        st.success(
                            f"✅ LLM extraction complete: "
                            f"{confidence:.0%} confidence, "
                            f"{llm_result['tokens_used']} tokens, "
                            f"{llm_result['extraction_time_ms']}ms"
                        )

                        st.subheader("📋 Extracted Fields")
                        col_a, col_b = st.columns(2)
                        fields = validated
                        field_items = list(fields.items())
                        mid = len(field_items) // 2

                        with col_a:
                            for key, val in field_items[:mid]:
                                if val and key != "transactions":
                                    st.markdown(f"**{key.replace('_', ' ').title()}:** {val}")

                        with col_b:
                            for key, val in field_items[mid:]:
                                if val and key != "transactions":
                                    st.markdown(f"**{key.replace('_', ' ').title()}:** {val}")

                        transactions = fields.get("transactions", [])
                        if transactions:
                            st.subheader(f"💳 Extracted Transactions ({len(transactions)})")
                            import pandas as pd
                            df_txns = pd.DataFrame(transactions)
                            st.dataframe(df_txns, use_container_width=True)

                        st.divider()
                        st.info("🔍 Step 3/4: Running agent analysis...")

                        from agents.graph import run_analysis
                        query = (
                            f"Analyse this {doc_type.replace('_', ' ')} document. "
                            f"Extracted data: {str(validated)[:500]}. "
                            f"Identify any risks, anomalies or concerns."
                        )
                        result = run_analysis(query)
                        decision = result.get("final_decision", {})

                        st.info("📝 Step 4/4: Saving results...")

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
                        if risk == "HIGH":
                            st.error(f"🔴 Risk Rating: {risk}")
                        elif risk == "MEDIUM":
                            st.warning(f"🟡 Risk Rating: {risk}")
                        else:
                            st.success(f"🟢 Risk Rating: {risk}")

                        st.subheader("📋 Executive Summary")
                        st.info(decision.get("executive_summary", "No summary available"))

                        st.subheader("⚡ Recommended Actions")
                        for action in decision.get("recommended_actions", []):
                            priority = action.get("priority", "monitor").upper()
                            if priority == "IMMEDIATE":
                                st.error(f"🔴 **{priority}**: {action.get('action', '')}")
                            elif priority == "SOON":
                                st.warning(f"🟡 **{priority}**: {action.get('action', '')}")
                            else:
                                st.info(f"🔵 **{priority}**: {action.get('action', '')}")

                        st.success(f"✅ Document fully processed and analysed. Document ID: {doc_id[:8]}...")

                        # ── Export Report Button ──────────────────────────────
                        st.divider()
                        if st.button("📄 Export PDF Report", use_container_width=True, key="export_upload_report"):
                            with st.spinner("Generating professional PDF report..."):
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
                                        label="⬇️ Download Report",
                                        data=f,
                                        file_name=os.path.basename(report_path),
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key="download_upload_report"
                                    )
                                st.success(f"✅ Report generated successfully")

                        os.unlink(tmp_path)

                    except Exception as e:
                        st.error(f"Processing failed: {str(e)}")
                        st.exception(e)

    # ── TAB 3: SQL Search ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("🔎 Natural Language Transaction Search")
        st.markdown("Ask questions in plain English — an AI agent converts it into a safe database query.")
        st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            sql_query = st.text_input(
                "Ask a question:",
                value=st.session_state.get("sql_query_input", ""),
                placeholder="e.g. Show me all transactions over AED 10,000"
            )
        with col2:
            st.markdown("**Try these:**")
            if st.button("💰 Large transactions", use_container_width=True):
                st.session_state["sql_query_input"] = "Show me all transactions over AED 10,000"
                st.rerun()
            if st.button("🚩 Flagged items", use_container_width=True):
                st.session_state["sql_query_input"] = "What flagged transactions do we have?"
                st.rerun()
            if st.button("🏦 Salary payments", use_container_width=True):
                st.session_state["sql_query_input"] = "Show me all salary transactions"
                st.rerun()

        st.divider()

        if st.button("🔍 Search", type="primary", use_container_width=True):
            if not sql_query:
                st.error("Please enter a question first")
            else:
                with st.spinner("🤖 Converting your question into a safe query..."):
                    try:
                        from agents.sql_agent import query_with_natural_language
                        result = query_with_natural_language(sql_query)

                        st.success(f"✅ {result['explanation']}")

                        with st.expander("🔧 Technical details (filters applied)"):
                            for f in result["applied_filters"]:
                                st.code(f, language="sql")

                        st.markdown(f"**{result['result_count']} results found**")

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

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 Financial Intelligence Dashboard")
    st.markdown("*Gold layer KPIs — updated after every pipeline run*")
    st.divider()

    supabase = get_supabase()

    st.subheader("💰 Spend by Category")
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
                color_continuous_scale="Blues",
                title="Total Spend by Category (AED)",
                labels={"total_amount": "Amount (AED)", "category": "Category"}
            )
            fig.update_layout(showlegend=False)
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
            st.info("No data yet. Run the Gold pipeline first.")
    except Exception as e:
        st.error(f"Error loading categories: {e}")

    st.divider()

    st.subheader("📈 Monthly Trends")
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
                title="Monthly Credit vs Debit (AED)",
                labels={"value": "Amount (AED)", "period": "Month"},
                color_discrete_map={"total_credit": "green", "total_debit": "red"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No trend data yet.")
    except Exception as e:
        st.error(f"Error loading trends: {e}")

    st.divider()

    st.subheader("🚩 Flagged Transaction Summary")
    try:
        result = supabase.table("gold_flagged_summary").select("*").execute()
        flagged = result.data

        if flagged:
            import plotly.express as px
            import pandas as pd
            df_flagged = pd.DataFrame(flagged)
            fig3 = px.pie(
                df_flagged, names="flag_reason_type", values="total_amount",
                title="Flagged Amounts by Type (AED)"
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No flagged transactions.")
    except Exception as e:
        st.error(f"Error loading flagged summary: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: REVIEW QUEUE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚩 Review Queue":
    st.title("🚩 Human Review Queue")
    st.markdown("*Flagged transactions requiring human approval*")
    st.divider()

    supabase = get_supabase()

    try:
        result = supabase.table("transactions").select("*").eq("is_flagged", True).execute()
        flagged_txns = result.data

        if not flagged_txns:
            st.success("✅ No flagged transactions. All clear!")
        else:
            st.warning(f"⚠️ {len(flagged_txns)} transactions require review")
            st.divider()

            for txn in flagged_txns:
                amount = float(txn.get("amount", 0))

                if amount > 75000:
                    risk_badge = "🔴 HIGH RISK"
                elif amount > 20000:
                    risk_badge = "🟡 MEDIUM RISK"
                else:
                    risk_badge = "🔵 LOW RISK"

                with st.expander(
                    f"{risk_badge} | {txn.get('description', 'Unknown')} | "
                    f"AED {amount:,.2f} | {txn.get('transaction_date', '')}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Description:** {txn.get('description', '')}")
                        st.markdown(f"**Amount:** AED {amount:,.2f}")
                        st.markdown(f"**Type:** {txn.get('transaction_type', '').upper()}")
                        st.markdown(f"**Category:** {txn.get('category', '')}")
                    with col2:
                        st.markdown(f"**Date:** {txn.get('transaction_date', '')}")
                        st.markdown(f"**Flag Reason:** {txn.get('flag_reason', '')}")
                        st.markdown(f"**Currency:** {txn.get('currency', 'AED')}")

                    st.divider()
                    notes = st.text_input("Reviewer notes (optional):", key=f"notes_{txn['id']}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ Approve", key=f"approve_{txn['id']}", use_container_width=True):
                            supabase.table("review_queue").insert({
                                "transaction_id": txn["id"],
                                "run_id": str(uuid.uuid4()),
                                "flag_reason": txn.get("flag_reason", ""),
                                "risk_level": "high" if amount > 75000 else "medium",
                                "status": "approved",
                                "reviewer_notes": notes,
                                "reviewed_at": datetime.utcnow().isoformat()
                            }).execute()
                            st.success("✅ Transaction approved")
                            st.rerun()

                    with col_b:
                        if st.button("❌ Reject", key=f"reject_{txn['id']}", use_container_width=True):
                            supabase.table("review_queue").insert({
                                "transaction_id": txn["id"],
                                "run_id": str(uuid.uuid4()),
                                "flag_reason": txn.get("flag_reason", ""),
                                "risk_level": "high" if amount > 75000 else "medium",
                                "status": "rejected",
                                "reviewer_notes": notes,
                                "reviewed_at": datetime.utcnow().isoformat()
                            }).execute()
                            st.error("❌ Transaction rejected")
                            st.rerun()

    except Exception as e:
        st.error(f"Error loading review queue: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Audit Log":
    st.title("📋 Audit Log")
    st.markdown("*Complete governance trail of all agent decisions*")
    st.divider()

    supabase = get_supabase()

    try:
        result = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
        logs = result.data

        if not logs:
            st.info("No audit logs yet. Run an analysis first.")
        else:
            st.success(f"Showing {len(logs)} most recent audit entries")
            st.divider()

            run_ids = list(dict.fromkeys([l["run_id"] for l in logs]))

            for run_id in run_ids[:5]:
                run_logs = [l for l in logs if l["run_id"] == run_id]
                first_log = run_logs[0]

                with st.expander(
                    f"Run: {run_id[:8]}... | "
                    f"{first_log.get('created_at', '')[:19]} | "
                    f"{len(run_logs)} agent entries"
                ):
                    for log in run_logs:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"**{log.get('agent_name', '').upper()}**")
                            st.markdown(f"`{log.get('action', '')}`")
                        with col2:
                            st.markdown(f"**Decision:** {log.get('decision', '')}")
                            st.markdown(f"**Reasoning:** {log.get('reasoning', '')[:150]}")
                        st.divider()

        st.subheader("📊 Run Metrics")
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

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: SYSTEM HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ System Health":
    st.title("⚙️ System Health")
    st.markdown("*LLMOps observability — tokens, costs, agent performance*")
    st.divider()

    try:
        from llmops.dashboard import get_system_health, get_agent_performance

        health = get_system_health()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Documents", health["total_documents"])
        col2.metric("Total Transactions", health["total_transactions"])
        col3.metric("Flagged Transactions", health["flagged_transactions"], delta="Need Review", delta_color="inverse")
        col4.metric("Agent Runs", health["total_agent_runs"])

        st.divider()

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Total Tokens Used", f"{health['total_tokens_used']:,}")
        col6.metric("Total Cost (USD)", f"${health['total_cost_usd']:.4f}")
        col7.metric("Audit Log Entries", health["total_audit_entries"])
        col8.metric("System Status", health["system_status"].upper(), delta="Online", delta_color="normal")

        st.divider()

        st.subheader("🤖 Agent Performance")
        perf = get_agent_performance()

        if perf:
            import pandas as pd
            df_perf = pd.DataFrame(perf)
            df_perf = df_perf[["agent_name", "total_calls"]].rename(columns={"agent_name": "Agent", "total_calls": "Total Calls"})
            st.dataframe(df_perf, use_container_width=True)

            import plotly.express as px
            fig = px.bar(
                df_perf, x="Agent", y="Total Calls", color="Total Calls",
                color_continuous_scale="Blues", title="Agent Call Frequency"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("🔄 Pipeline Status")
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

        st.subheader("🔬 Extraction Results")
        ext_result = supabase.table("extraction_results").select("*").execute()
        extractions = ext_result.data

        if extractions:
            for ext in extractions:
                doc_id = ext.get("document_id", "")[:8]
                model = ext.get("model_used", "")
                tokens = ext.get("tokens_used", 0)
                time_ms = ext.get("extraction_time_ms", 0)
                confidence = ext.get("confidence_scores", {})

                with st.expander(f"Document: {doc_id}... | Model: {model} | Tokens: {tokens} | Time: {time_ms}ms"):
                    st.json(confidence)
                    fields = ext.get("extracted_fields", {})
                    st.json(fields)
        else:
            st.info("No extraction results yet. Run the extraction pipeline first.")

    except Exception as e:
        st.error(f"Error loading system health: {e}")
        st.exception(e)