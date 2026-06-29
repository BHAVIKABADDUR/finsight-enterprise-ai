# ingestion/generate_synthetic_data.py
# Generates realistic UAE financial documents for testing

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

# ── Seed for reproducibility ──────────────────────────────────────────────────
random.seed(42)

# ── Realistic UAE data pools ──────────────────────────────────────────────────
UAE_COMPANIES = [
    "Emirates NBD", "ADCB Bank", "Dubai Islamic Bank",
    "Careem Technologies", "Noon.com LLC", "Emaar Properties",
    "DEWA - Dubai Electricity", "Etisalat by e&", "du Telecom",
    "LuLu Hypermarket", "Spinneys Dubai", "Al Futtaim Group",
    "Majid Al Futtaim", "Mashreq Bank", "First Abu Dhabi Bank",
    "Transguard Group", "Aramex International", "Flydubai Airlines",
    "Dubai Airports", "Abu Dhabi National Energy"
]

UAE_CATEGORIES = [
    "Salary", "Vendor Payment", "Utility Bill", "Telecom",
    "Rent", "Transfer", "Retail Purchase", "Insurance",
    "Government Fee", "Subscription"
]

UAE_IBANS = [
    f"AE{random.randint(10,99)}0330000019{random.randint(1000000,9999999)}"
    for _ in range(10)
]

CURRENCIES = ["AED", "AED", "AED", "USD", "EUR"]  # AED weighted higher

def random_date(start_days_ago=90):
    """Generate a random date within the last N days."""
    start = datetime.now() - timedelta(days=start_days_ago)
    random_days = random.randint(0, start_days_ago)
    return start + timedelta(days=random_days)

def random_amount(min_val=50, max_val=50000):
    """Generate a realistic transaction amount."""
    return round(random.uniform(min_val, max_val), 2)

def inject_anomalies(transactions):
    """
    Inject realistic anomalies into transactions.
    This gives our AI agents something meaningful to detect.
    """
    anomalies = []

    # Anomaly 1: Duplicate transaction
    if len(transactions) > 5:
        duplicate = transactions[2].copy()
        duplicate["description"] = transactions[2]["description"]
        duplicate["amount"] = transactions[2]["amount"]
        duplicate["flag_reason"] = "Duplicate transaction detected"
        anomalies.append(duplicate)

    # Anomaly 2: Unusually large amount
    large_txn = {
        "date": random_date(10).strftime("%Y-%m-%d"),
        "description": "UNKNOWN VENDOR TRANSFER",
        "amount": round(random.uniform(95000, 150000), 2),
        "type": "debit",
        "category": "Transfer",
        "currency": "AED",
        "flag_reason": "Unusually large transaction amount"
    }
    anomalies.append(large_txn)

    # Anomaly 3: Suspicious round number
    round_txn = {
        "date": random_date(5).strftime("%Y-%m-%d"),
        "description": "CASH WITHDRAWAL",
        "amount": 50000.00,
        "type": "debit",
        "category": "Transfer",
        "currency": "AED",
        "flag_reason": "Suspicious round number transaction"
    }
    anomalies.append(round_txn)

    return transactions + anomalies

def generate_transactions(num=20):
    """Generate a list of realistic UAE transactions."""
    transactions = []
    for _ in range(num):
        txn_type = random.choice(["credit", "debit", "debit"])  # more debits
        transactions.append({
            "date": random_date().strftime("%Y-%m-%d"),
            "description": random.choice(UAE_COMPANIES),
            "amount": random_amount(),
            "type": txn_type,
            "category": random.choice(UAE_CATEGORIES),
            "currency": random.choice(CURRENCIES),
            "flag_reason": None
        })
    return inject_anomalies(transactions)

# ── Generator 1: Transaction CSV ──────────────────────────────────────────────
def generate_transaction_csv(output_dir, filename="transactions_q1_2026.csv"):
    """Generate a realistic transaction CSV file."""
    transactions = generate_transactions(30)
    filepath = Path(output_dir) / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "description", "amount", "type",
            "category", "currency", "flag_reason"
        ])
        writer.writeheader()
        writer.writerows(transactions)

    print(f"✅ Generated CSV: {filepath}")
    return str(filepath)

# ── Generator 2: Bank Statement PDF ──────────────────────────────────────────
def generate_bank_statement_pdf(output_dir, filename="bank_statement_jan_2026.pdf"):
    """Generate a realistic UAE bank statement PDF."""
    filepath = Path(output_dir) / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("Emirates NBD Bank", styles["Title"]))
    elements.append(Paragraph("Account Statement — January 2026", styles["Heading2"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Account info
    account_info = [
        ["Account Holder:", "Bhavika Baddur"],
        ["Account Number:", "1234567890"],
        ["IBAN:", UAE_IBANS[0]],
        ["Currency:", "AED"],
        ["Statement Period:", "01 Jan 2026 — 31 Jan 2026"],
        ["Opening Balance:", "AED 45,230.00"],
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

    # Transactions table
    elements.append(Paragraph("Transaction History", styles["Heading3"]))
    elements.append(Spacer(1, 0.3 * cm))

    transactions = generate_transactions(15)
    table_data = [["Date", "Description", "Amount (AED)", "Type", "Category"]]
    for txn in transactions:
        table_data.append([
            txn["date"],
            txn["description"][:30],
            f"{txn['amount']:,.2f}",
            txn["type"].upper(),
            txn["category"]
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

    # Closing balance
    elements.append(Paragraph("Closing Balance: AED 38,450.75", styles["Heading3"]))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        "This is a system-generated statement. For queries contact: 800-ENBD (3623)",
        styles["Normal"]
    ))

    doc.build(elements)
    print(f"✅ Generated Bank Statement PDF: {filepath}")
    return str(filepath)

# ── Generator 3: Invoice PDF ──────────────────────────────────────────────────
def generate_invoice_pdf(output_dir, filename="invoice_001_2026.pdf"):
    """Generate a realistic vendor invoice PDF."""
    filepath = Path(output_dir) / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    vendor = random.choice(UAE_COMPANIES)
    invoice_date = random_date(30).strftime("%d %b %Y")
    due_date = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
    invoice_number = f"INV-2026-{random.randint(1000, 9999)}"

    # Header
    elements.append(Paragraph(f"INVOICE", styles["Title"]))
    elements.append(Paragraph(vendor, styles["Heading2"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Invoice details
    invoice_info = [
        ["Invoice Number:", invoice_number],
        ["Invoice Date:", invoice_date],
        ["Due Date:", due_date],
        ["Bill To:", "Bhavika Baddur"],
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

    # Line items
    elements.append(Paragraph("Invoice Items", styles["Heading3"]))
    items = [
        ["Description", "Qty", "Unit Price (AED)", "Total (AED)"],
        ["Professional Services - Q1 2026", "1", "15,000.00", "15,000.00"],
        ["Software License Fee", "2", "3,500.00", "7,000.00"],
        ["Support & Maintenance", "1", "2,500.00", "2,500.00"],
        ["Cloud Infrastructure", "1", "1,200.00", "1,200.00"],
    ]
    subtotal = 25700.00
    vat = round(subtotal * 0.05, 2)
    total = subtotal + vat

    items.append(["", "", "Subtotal:", f"{subtotal:,.2f}"])
    items.append(["", "", "VAT (5%):", f"{vat:,.2f}"])
    items.append(["", "", "TOTAL DUE:", f"{total:,.2f}"])

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
    elements.append(Paragraph(
        f"Payment to be made to IBAN: {UAE_IBANS[1]}",
        styles["Normal"]
    ))

    doc.build(elements)
    print(f"✅ Generated Invoice PDF: {filepath}")
    return str(filepath)

# ── Main runner ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Create data directory (gitignored)
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating synthetic UAE financial documents...\n")
    generate_transaction_csv(output_dir)
    generate_bank_statement_pdf(output_dir)
    generate_invoice_pdf(output_dir)
    print("\n🎉 All synthetic data generated in data/raw/")