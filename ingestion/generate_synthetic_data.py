# ingestion/generate_synthetic_data.py
# Generates realistic UAE financial documents for testing
# Expanded version: 3 business accounts, 6 months of data

import os
import random
import csv
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import cm

random.seed(42)

# ── Realistic UAE data pools ──────────────────────────────────────────────────
UAE_COMPANIES = [
    "Emirates NBD", "ADCB Bank", "Dubai Islamic Bank",
    "Careem Technologies", "Noon.com LLC", "Emaar Properties",
    "DEWA - Dubai Electricity", "Etisalat by e&", "du Telecom",
    "LuLu Hypermarket", "Spinneys Dubai", "Al Futtaim Group",
    "Majid Al Futtaim", "Mashreq Bank", "First Abu Dhabi Bank",
    "Transguard Group", "Aramex International", "Flydubai Airlines",
    "Dubai Airports", "Abu Dhabi National Energy", "RTA Dubai",
    "Talabat", "Amazon.ae", "IKEA UAE", "Carrefour UAE"
]

UAE_CATEGORIES = [
    "Salary", "Vendor Payment", "Utility Bill", "Telecom",
    "Rent", "Transfer", "Retail Purchase", "Insurance",
    "Government Fee", "Subscription", "Logistics", "Marketing"
]

CURRENCIES = ["AED", "AED", "AED", "AED", "USD", "EUR"]

# ── Business accounts (multi-entity) ──────────────────────────────────────────
ACCOUNTS = [
    {
        "name": "Bhavika Baddur Trading LLC",
        "account_number": "1234567890",
        "iban": "AE910330000019" + str(random.randint(1000000, 9999999)),
        "bank": "Emirates NBD Bank",
        "risk_profile": "low"
    },
    {
        "name": "Gulf Horizon Consulting FZE",
        "account_number": "2345678901",
        "iban": "AE920330000019" + str(random.randint(1000000, 9999999)),
        "bank": "ADCB Bank",
        "risk_profile": "high"
    },
    {
        "name": "Desert Rose Retail Co",
        "account_number": "3456789012",
        "iban": "AE930330000019" + str(random.randint(1000000, 9999999)),
        "bank": "Dubai Islamic Bank",
        "risk_profile": "medium"
    }
]

def random_date_in_month(year: int, month: int):
    """Generate a random date within a specific month."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    start = datetime(year, month, 1)
    days_in_month = (next_month - start).days
    return start + timedelta(days=random.randint(0, days_in_month - 1))

def random_amount(min_val=50, max_val=50000):
    return round(random.uniform(min_val, max_val), 2)

def inject_anomalies(transactions, risk_profile="medium"):
    """
    Inject anomalies scaled by account risk profile.
    High risk accounts get more anomalies.
    """
    anomalies = []
    anomaly_count = {"low": 1, "medium": 2, "high": 4}.get(risk_profile, 2)

    if len(transactions) > 5:
        duplicate = transactions[2].copy()
        duplicate["flag_reason"] = "Duplicate transaction detected"
        anomalies.append(duplicate)

    for i in range(anomaly_count):
        choice = random.choice(["large", "round", "unknown"])

        if choice == "large":
            anomalies.append({
                "date": transactions[0]["date"] if transactions else datetime.now().strftime("%Y-%m-%d"),
                "description": "UNKNOWN VENDOR TRANSFER",
                "amount": round(random.uniform(80000, 200000), 2),
                "type": "debit",
                "category": "Transfer",
                "currency": "AED",
                "flag_reason": "Unusually large transaction amount"
            })
        elif choice == "round":
            anomalies.append({
                "date": transactions[0]["date"] if transactions else datetime.now().strftime("%Y-%m-%d"),
                "description": "CASH WITHDRAWAL",
                "amount": float(random.choice([30000, 40000, 50000, 60000])),
                "type": "debit",
                "category": "Transfer",
                "currency": "AED",
                "flag_reason": "Suspicious round number transaction"
            })
        else:
            anomalies.append({
                "date": transactions[0]["date"] if transactions else datetime.now().strftime("%Y-%m-%d"),
                "description": "UNVERIFIED THIRD PARTY PAYMENT",
                "amount": round(random.uniform(15000, 60000), 2),
                "type": "debit",
                "category": "Vendor Payment",
                "currency": "AED",
                "flag_reason": "Unknown vendor with no transaction history"
            })

    return transactions + anomalies

def generate_monthly_transactions(year: int, month: int, num: int, risk_profile: str):
    """Generate transactions for a specific month."""
    transactions = []
    for _ in range(num):
        txn_type = random.choice(["credit", "debit", "debit", "debit"])
        transactions.append({
            "date": random_date_in_month(year, month).strftime("%Y-%m-%d"),
            "description": random.choice(UAE_COMPANIES),
            "amount": random_amount(),
            "type": txn_type,
            "category": random.choice(UAE_CATEGORIES),
            "currency": random.choice(CURRENCIES),
            "flag_reason": None
        })
    return inject_anomalies(transactions, risk_profile)

# ── Generator 1: Transaction CSV (per account, 6 months) ─────────────────────
def generate_transaction_csv(output_dir, account: dict, base_year=2026):
    """Generate a 6-month transaction CSV for one account."""
    safe_name = account["name"].replace(" ", "_").replace(".", "")
    filename = f"transactions_{safe_name}_2026.csv"
    filepath = Path(output_dir) / filename

    all_transactions = []
    months = [(base_year, m) for m in range(1, 7)]  # Jan-Jun 2026

    for year, month in months:
        monthly = generate_monthly_transactions(
            year, month, num=random.randint(12, 20),
            risk_profile=account["risk_profile"]
        )
        all_transactions.extend(monthly)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "description", "amount", "type",
            "category", "currency", "flag_reason"
        ])
        writer.writeheader()
        writer.writerows(all_transactions)

    print(f"✅ Generated CSV: {filepath} ({len(all_transactions)} transactions)")
    return str(filepath), len(all_transactions)

# ── Generator 2: Bank Statement PDF (per account) ─────────────────────────────
def generate_bank_statement_pdf(output_dir, account: dict, month_name="June"):
    safe_name = account["name"].replace(" ", "_").replace(".", "")
    filename = f"bank_statement_{safe_name}_{month_name}_2026.pdf"
    filepath = Path(output_dir) / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(account["bank"], styles["Title"]))
    elements.append(Paragraph(f"Account Statement — {month_name} 2026", styles["Heading2"]))
    elements.append(Spacer(1, 0.5 * cm))

    account_info = [
        ["Account Holder:", account["name"]],
        ["Account Number:", account["account_number"]],
        ["IBAN:", account["iban"]],
        ["Currency:", "AED"],
        ["Statement Period:", f"01 {month_name} 2026 — 30 {month_name} 2026"],
        ["Opening Balance:", f"AED {random.uniform(20000, 80000):,.2f}"],
    ]
    info_table = Table(account_info, colWidths=[5 * cm, 10 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Transaction History", styles["Heading3"]))
    elements.append(Spacer(1, 0.3 * cm))

    transactions = generate_monthly_transactions(
        2026, 6, num=15, risk_profile=account["risk_profile"]
    )
    table_data = [["Date", "Description", "Amount (AED)", "Type", "Category"]]
    for txn in transactions[:15]:
        table_data.append([
            txn["date"], txn["description"][:30],
            f"{txn['amount']:,.2f}", txn["type"].upper(), txn["category"]
        ])

    txn_table = Table(table_data, colWidths=[3*cm, 6*cm, 3.5*cm, 2.5*cm, 3.5*cm])
    txn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(txn_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Closing Balance: AED {random.uniform(15000, 70000):,.2f}", styles["Heading3"]))

    doc.build(elements)
    print(f"✅ Generated Bank Statement PDF: {filepath}")
    return str(filepath)

# ── Generator 3: Invoice PDF (multiple per account) ───────────────────────────
def generate_invoice_pdf(output_dir, account: dict, invoice_num: int):
    filename = f"invoice_{invoice_num:03d}_2026.pdf"
    filepath = Path(output_dir) / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    vendor = random.choice(UAE_COMPANIES)
    invoice_date = random_date_in_month(2026, random.randint(1, 6)).strftime("%d %b %Y")
    due_date = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
    invoice_number = f"INV-2026-{random.randint(1000, 9999)}"

    elements.append(Paragraph("INVOICE", styles["Title"]))
    elements.append(Paragraph(vendor, styles["Heading2"]))
    elements.append(Spacer(1, 0.5 * cm))

    invoice_info = [
        ["Invoice Number:", invoice_number],
        ["Invoice Date:", invoice_date],
        ["Due Date:", due_date],
        ["Bill To:", account["name"]],
        ["Payment Terms:", "Net 30"],
    ]
    info_table = Table(invoice_info, colWidths=[5 * cm, 10 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Invoice Items", styles["Heading3"]))
    subtotal = round(random.uniform(8000, 30000), 2)
    vat = round(subtotal * 0.05, 2)
    total = subtotal + vat

    items = [
        ["Description", "Qty", "Unit Price (AED)", "Total (AED)"],
        [f"Professional Services - {random.choice(['Q1', 'Q2'])} 2026", "1", f"{subtotal*0.6:,.2f}", f"{subtotal*0.6:,.2f}"],
        ["Software License Fee", "2", f"{subtotal*0.25/2:,.2f}", f"{subtotal*0.25:,.2f}"],
        ["Support & Maintenance", "1", f"{subtotal*0.15:,.2f}", f"{subtotal*0.15:,.2f}"],
        ["", "", "Subtotal:", f"{subtotal:,.2f}"],
        ["", "", "VAT (5%):", f"{vat:,.2f}"],
        ["", "", "TOTAL DUE:", f"{total:,.2f}"],
    ]

    items_table = Table(items, colWidths=[8*cm, 2*cm, 4*cm, 4*cm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -4), 0.5, colors.grey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Payment to be made to IBAN: {account['iban']}", styles["Normal"]))

    doc.build(elements)
    print(f"✅ Generated Invoice PDF: {filepath}")
    return str(filepath)

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating expanded synthetic UAE financial dataset...")
    print(f"Accounts: {len(ACCOUNTS)} | Period: Jan-Jun 2026\n")

    total_transactions = 0

    for account in ACCOUNTS:
        print(f"\n── {account['name']} ({account['risk_profile']} risk) ──")
        _, count = generate_transaction_csv(output_dir, account)
        total_transactions += count
        generate_bank_statement_pdf(output_dir, account)

    # Generate several invoices across accounts
    for i, account in enumerate(ACCOUNTS, start=1):
        for j in range(2):  # 2 invoices per account
            generate_invoice_pdf(output_dir, account, invoice_num=i * 10 + j)

    print(f"\n🎉 Dataset generation complete!")
    print(f"   Total transactions across all accounts: {total_transactions}")
    print(f"   Accounts: {len(ACCOUNTS)}")
    print(f"   Files saved to: data/raw/")