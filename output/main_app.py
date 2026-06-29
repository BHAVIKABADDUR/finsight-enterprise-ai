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
    ["🏠 Analysis", "📊 Dashboard", "🚩 Review Queue", "📋 Audit Log"]
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

    # Query input
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

                    decision = result.get("final_decision", {})
                    analysis = result.get("analysis_results", {})
                    extracted = result.get("extracted_data", {})

                    # ── Risk Rating Banner ────────────────────────────────────
                    risk = decision.get("overall_risk_rating", "UNKNOWN")
                    if risk == "HIGH":
                        st.error(f"🔴 Risk Rating: {risk}")
                    elif risk == "MEDIUM":
                        st.warning(f"🟡 Risk Rating: {risk}")
                    else:
                        st.success(f"🟢 Risk Rating: {risk}")

                    st.divider()

                    # ── Executive Summary ─────────────────────────────────────
                    st.subheader("📋 Executive Summary")
                    st.info(decision.get("executive_summary", "No summary available"))

                    # ── Key Metrics ───────────────────────────────────────────
                    st.subheader("📊 Key Metrics")
                    txn_summary = extracted.get(
                        "transactions", {}
                    ).get("summary", {})

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric(
                        "Total Transactions",
                        txn_summary.get("total_count", 0)
                    )
                    col2.metric(
                        "Total Credit",
                        f"AED {txn_summary.get('total_credit_aed', 0):,.0f}"
                    )
                    col3.metric(
                        "Total Debit",
                        f"AED {txn_summary.get('total_debit_aed', 0):,.0f}"
                    )
                    col4.metric(
                        "Flagged",
                        txn_summary.get("flagged_count", 0),
                        delta="Needs Review",
                        delta_color="inverse"
                    )

                    st.divider()

                    # ── Recommended Actions ───────────────────────────────────
                    st.subheader("⚡ Recommended Actions")
                    actions = decision.get("recommended_actions", [])
                    for action in actions:
                        priority = action.get("priority", "monitor").upper()
                        if priority == "IMMEDIATE":
                            st.error(
                                f"🔴 **{priority}**: {action.get('action', '')}"
                            )
                        elif priority == "SOON":
                            st.warning(
                                f"🟡 **{priority}**: {action.get('action', '')}"
                            )
                        else:
                            st.info(
                                f"🔵 **{priority}**: {action.get('action', '')}"
                            )

                    st.divider()

                    # ── Primary Concerns ──────────────────────────────────────
                    st.subheader("⚠️ Primary Concerns")
                    for concern in decision.get("primary_concerns", []):
                        st.markdown(f"• {concern}")

                    # ── Human Review Alert ────────────────────────────────────
                    if decision.get("requires_human_review"):
                        st.divider()
                        st.warning(
                            f"👤 **Human Review Required**: "
                            f"{decision.get('human_review_reason', '')}"
                        )
                        st.markdown(
                            "Go to **🚩 Review Queue** to approve or reject flagged items."
                        )

                    st.success(
                        f"✅ Analysis complete. Run ID: {result.get('run_id', 'N/A')}"
                    )

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.title("📊 Financial Intelligence Dashboard")
    st.markdown("*Gold layer KPIs — updated after every pipeline run*")
    st.divider()

    supabase = get_supabase()

    # ── Spend by Category ─────────────────────────────────────────────────────
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
                df,
                x="category",
                y="total_amount",
                color="total_amount",
                color_continuous_scale="Blues",
                title="Total Spend by Category (AED)",
                labels={"total_amount": "Amount (AED)", "category": "Category"}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[["category", "total_amount", "transaction_count", "avg_amount"]].rename(
                    columns={
                        "category": "Category",
                        "total_amount": "Total (AED)",
                        "transaction_count": "Count",
                        "avg_amount": "Average (AED)"
                    }
                ),
                use_container_width=True
            )
        else:
            st.info("No data yet. Run the Gold pipeline first.")
    except Exception as e:
        st.error(f"Error loading categories: {e}")

    st.divider()

    # ── Monthly Trends ────────────────────────────────────────────────────────
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
                df_trends,
                x="period",
                y=["total_credit", "total_debit"],
                title="Monthly Credit vs Debit (AED)",
                labels={"value": "Amount (AED)", "period": "Month"},
                color_discrete_map={
                    "total_credit": "green",
                    "total_debit": "red"
                }
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No trend data yet.")
    except Exception as e:
        st.error(f"Error loading trends: {e}")

    st.divider()

    # ── Flagged Summary ───────────────────────────────────────────────────────
    st.subheader("🚩 Flagged Transaction Summary")
    try:
        result = supabase.table("gold_flagged_summary").select("*").execute()
        flagged = result.data

        if flagged:
            import plotly.express as px
            import pandas as pd
            df_flagged = pd.DataFrame(flagged)
            fig3 = px.pie(
                df_flagged,
                names="flag_reason_type",
                values="total_amount",
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
        result = supabase.table("transactions").select("*").eq(
            "is_flagged", True
        ).execute()
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
                    notes = st.text_input(
                        "Reviewer notes (optional):",
                        key=f"notes_{txn['id']}"
                    )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(
                            "✅ Approve",
                            key=f"approve_{txn['id']}",
                            use_container_width=True
                        ):
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
                        if st.button(
                            "❌ Reject",
                            key=f"reject_{txn['id']}",
                            use_container_width=True
                        ):
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
        result = supabase.table("audit_logs").select("*").order(
            "created_at", desc=True
        ).limit(50).execute()
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
                            st.markdown(
                                f"**Reasoning:** {log.get('reasoning', '')[:150]}"
                            )
                        st.divider()

        st.subheader("📊 Run Metrics")
        metrics_result = supabase.table("run_metrics").select("*").order(
            "created_at", desc=True
        ).limit(10).execute()
        metrics = metrics_result.data

        if metrics:
            import pandas as pd
            df_metrics = pd.DataFrame(metrics)
            st.dataframe(
                df_metrics[[
                    "run_id", "total_tokens", "total_cost_usd",
                    "transactions_extracted", "flags_raised", "status"
                ]].rename(columns={
                    "run_id": "Run ID",
                    "total_tokens": "Tokens",
                    "total_cost_usd": "Cost (USD)",
                    "transactions_extracted": "Transactions",
                    "flags_raised": "Flags",
                    "status": "Status"
                }),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error loading audit log: {e}")