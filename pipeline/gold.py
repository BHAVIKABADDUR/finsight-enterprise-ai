# pipeline/gold.py
# Gold Layer — KPI aggregations from Silver data
# Produces business-ready summaries for dashboards and agents

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from loguru import logger

load_dotenv()

# ── Supabase client ───────────────────────────────────────────────────────────
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

# ── KPI 1: Spend by category ──────────────────────────────────────────────────
def compute_spend_by_category(supabase: Client) -> list:
    """
    Aggregate total spend, count and average by category.
    Only includes debit transactions (actual spend).
    """
    logger.info("Computing spend by category...")

    result = supabase.table("transactions").select(
        "category, amount, currency"
    ).eq("transaction_type", "debit").execute()

    transactions = result.data

    # Group by category in Python
    category_map = {}
    for txn in transactions:
        cat = txn.get("category", "Unknown")
        amount = float(txn.get("amount", 0))

        if cat not in category_map:
            category_map[cat] = {
                "total_amount": 0,
                "transaction_count": 0,
                "currency": txn.get("currency", "AED")
            }

        category_map[cat]["total_amount"] += amount
        category_map[cat]["transaction_count"] += 1

    # Build records
    records = []
    for category, data in category_map.items():
        count = data["transaction_count"]
        total = data["total_amount"]
        records.append({
            "category": category,
            "total_amount": round(total, 2),
            "transaction_count": count,
            "avg_amount": round(total / count, 2) if count > 0 else 0,
            "currency": data["currency"]
        })

    # Sort by total amount descending
    records.sort(key=lambda x: x["total_amount"], reverse=True)

    logger.success(f"Computed {len(records)} category KPIs")
    return records

# ── KPI 2: Monthly trends ─────────────────────────────────────────────────────
def compute_monthly_trends(supabase: Client) -> list:
    """
    Aggregate transaction volumes and amounts by month.
    Shows credit vs debit split and flagged count per month.
    """
    logger.info("Computing monthly trends...")

    result = supabase.table("transactions").select(
        "transaction_date, amount, transaction_type, is_flagged"
    ).execute()

    transactions = result.data

    # Group by year-month
    monthly_map = {}
    for txn in transactions:
        date_str = txn.get("transaction_date", "")
        if not date_str:
            continue

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            key = f"{date.year}-{date.month:02d}"
            year = date.year
            month = date.strftime("%B")
        except ValueError:
            continue

        if key not in monthly_map:
            monthly_map[key] = {
                "month": month,
                "year": year,
                "total_credit": 0,
                "total_debit": 0,
                "transaction_count": 0,
                "flagged_count": 0
            }

        amount = float(txn.get("amount", 0))
        txn_type = txn.get("transaction_type", "debit")
        is_flagged = txn.get("is_flagged", False)

        if txn_type == "credit":
            monthly_map[key]["total_credit"] += amount
        else:
            monthly_map[key]["total_debit"] += amount

        monthly_map[key]["transaction_count"] += 1

        if is_flagged:
            monthly_map[key]["flagged_count"] += 1

    # Build records
    records = []
    for key, data in monthly_map.items():
        records.append({
            "month": data["month"],
            "year": data["year"],
            "total_credit": round(data["total_credit"], 2),
            "total_debit": round(data["total_debit"], 2),
            "transaction_count": data["transaction_count"],
            "flagged_count": data["flagged_count"]
        })

    # Sort by year then month
    records.sort(key=lambda x: (x["year"], x["month"]))

    logger.success(f"Computed {len(records)} monthly trend KPIs")
    return records

# ── KPI 3: Flagged transaction summary ────────────────────────────────────────
def compute_flagged_summary(supabase: Client) -> list:
    """
    Summarize flagged transactions by reason type.
    This feeds directly into the agent decision layer.
    """
    logger.info("Computing flagged transaction summary...")

    result = supabase.table("transactions").select(
        "flag_reason, amount"
    ).eq("is_flagged", True).execute()

    flagged = result.data

    if not flagged:
        logger.info("No flagged transactions found")
        return []

    # Group by flag reason type
    reason_map = {}
    for txn in flagged:
        reason = txn.get("flag_reason", "Unknown")
        amount = float(txn.get("amount", 0))

        # Simplify reason to a type
        if "large" in reason.lower():
            reason_type = "Large Amount"
        elif "duplicate" in reason.lower():
            reason_type = "Duplicate"
        elif "round" in reason.lower():
            reason_type = "Suspicious Round Number"
        elif "unknown" in reason.lower():
            reason_type = "Unknown Vendor"
        elif "invalid" in reason.lower():
            reason_type = "Invalid Amount"
        else:
            reason_type = "Other"

        if reason_type not in reason_map:
            reason_map[reason_type] = {"count": 0, "total_amount": 0}

        reason_map[reason_type]["count"] += 1
        reason_map[reason_type]["total_amount"] += amount

    records = []
    for reason_type, data in reason_map.items():
        records.append({
            "flag_reason_type": reason_type,
            "count": data["count"],
            "total_amount": round(data["total_amount"], 2)
        })

    records.sort(key=lambda x: x["total_amount"], reverse=True)

    logger.success(f"Computed {len(records)} flagged summary KPIs")
    return records

# ── Write KPIs to Supabase ────────────────────────────────────────────────────
def write_gold_kpis(supabase: Client, table: str, records: list):
    """
    Write KPI records to a Gold table.
    Clears old records first so KPIs are always fresh.
    """
    if not records:
        logger.warning(f"No records to write to {table}")
        return

    # Delete old KPIs (we recompute from scratch each time)
    supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Insert fresh KPIs
    supabase.table(table).insert(records).execute()
    logger.success(f"Written {len(records)} records to {table}")

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    supabase = get_supabase_client()

    logger.info("Starting Gold Layer computation...")

    # Compute all KPIs
    spend_by_category = compute_spend_by_category(supabase)
    monthly_trends = compute_monthly_trends(supabase)
    flagged_summary = compute_flagged_summary(supabase)

    # Write to Gold tables
    write_gold_kpis(supabase, "gold_spend_by_category", spend_by_category)
    write_gold_kpis(supabase, "gold_monthly_trends", monthly_trends)
    write_gold_kpis(supabase, "gold_flagged_summary", flagged_summary)

    print("\n── Gold Layer Results ──")
    print(f"  Spend by category: {len(spend_by_category)} categories")
    for r in spend_by_category:
        print(f"    {r['category']}: AED {r['total_amount']:,.2f} ({r['transaction_count']} txns)")

    print(f"\n  Monthly trends: {len(monthly_trends)} months")
    for r in monthly_trends:
        print(f"    {r['month']} {r['year']}: "
              f"Credit AED {r['total_credit']:,.2f} | "
              f"Debit AED {r['total_debit']:,.2f} | "
              f"Flagged: {r['flagged_count']}")

    print(f"\n  Flagged summary: {len(flagged_summary)} flag types")
    for r in flagged_summary:
        print(f"    {r['flag_reason_type']}: "
              f"{r['count']} transactions, "
              f"AED {r['total_amount']:,.2f}")

    print(f"\n✅ Gold layer complete")