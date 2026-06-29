# mcp_servers/query_transactions.py
# MCP Server 1: Query transactions from Supabase
# Agents use this to filter, search and analyse transaction data

import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

# ── MCP Server setup ──────────────────────────────────────────────────────────
server = Server("query-transactions")

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

# ── Tool 1: Get all transactions ──────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_transactions",
            description=(
                "Query financial transactions from the database. "
                "Can filter by category, transaction type, flagged status, "
                "and limit the number of results returned."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category e.g. 'Salary', 'Vendor Payment', 'Transfer'"
                    },
                    "transaction_type": {
                        "type": "string",
                        "enum": ["credit", "debit"],
                        "description": "Filter by credit or debit transactions"
                    },
                    "flagged_only": {
                        "type": "boolean",
                        "description": "If true, return only flagged transactions"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 20)",
                        "default": 20
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_transaction_summary",
            description=(
                "Get a high-level summary of all transactions including "
                "total count, total credit, total debit, and flagged count."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_flagged_transactions",
            description=(
                "Get all flagged transactions with their flag reasons. "
                "Use this to understand what anomalies were detected."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "risk_level": {
                        "type": "string",
                        "description": "Optional filter: 'high', 'medium', 'low'"
                    }
                },
                "required": []
            }
        )
    ]

# ── Tool implementations ───────────────────────────────────────────────────────
@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:

    supabase = get_supabase()

    # ── get_transactions ──────────────────────────────────────────────────────
    if name == "get_transactions":
        query = supabase.table("transactions").select("*")

        if arguments.get("category"):
            query = query.eq("category", arguments["category"])

        if arguments.get("transaction_type"):
            query = query.eq("transaction_type", arguments["transaction_type"])

        if arguments.get("flagged_only"):
            query = query.eq("is_flagged", True)

        limit = arguments.get("limit", 20)
        query = query.limit(limit)

        result = query.execute()
        transactions = result.data

        # Format for agent readability
        formatted = []
        for t in transactions:
            formatted.append({
                "id": t["id"],
                "date": t["transaction_date"],
                "description": t["description"],
                "amount": f"AED {float(t['amount']):,.2f}",
                "type": t["transaction_type"],
                "category": t["category"],
                "flagged": t["is_flagged"],
                "flag_reason": t.get("flag_reason", "")
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "count": len(formatted),
                "transactions": formatted
            }, indent=2)
        )]

    # ── get_transaction_summary ───────────────────────────────────────────────
    elif name == "get_transaction_summary":
        result = supabase.table("transactions").select(
            "amount, transaction_type, is_flagged"
        ).execute()

        transactions = result.data
        total_credit = sum(
            float(t["amount"]) for t in transactions
            if t["transaction_type"] == "credit"
        )
        total_debit = sum(
            float(t["amount"]) for t in transactions
            if t["transaction_type"] == "debit"
        )
        flagged_count = sum(1 for t in transactions if t["is_flagged"])

        summary = {
            "total_transactions": len(transactions),
            "total_credit_aed": round(total_credit, 2),
            "total_debit_aed": round(total_debit, 2),
            "net_position_aed": round(total_credit - total_debit, 2),
            "flagged_count": flagged_count,
            "flagged_percentage": round(
                (flagged_count / len(transactions) * 100)
                if transactions else 0, 1
            )
        }

        return [types.TextContent(
            type="text",
            text=json.dumps(summary, indent=2)
        )]

    # ── get_flagged_transactions ──────────────────────────────────────────────
    elif name == "get_flagged_transactions":
        result = supabase.table("transactions").select("*").eq(
            "is_flagged", True
        ).execute()

        flagged = result.data
        formatted = []
        for t in flagged:
            amount = float(t["amount"])
            # Assign risk level based on amount
            if amount > 75000:
                risk = "high"
            elif amount > 20000:
                risk = "medium"
            else:
                risk = "low"

            if arguments.get("risk_level") and risk != arguments["risk_level"]:
                continue

            formatted.append({
                "id": t["id"],
                "date": t["transaction_date"],
                "description": t["description"],
                "amount": f"AED {amount:,.2f}",
                "flag_reason": t.get("flag_reason", ""),
                "risk_level": risk
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "flagged_count": len(formatted),
                "flagged_transactions": formatted
            }, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

# ── Run server ────────────────────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())