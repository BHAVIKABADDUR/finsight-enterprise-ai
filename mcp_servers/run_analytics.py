# mcp_servers/run_analytics.py
# MCP Server 3: Query Gold layer KPI tables
# Agents use this to get business intelligence summaries

import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

server = Server("run-analytics")

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_spend_by_category",
            description=(
                "Get total spend broken down by category from the Gold layer. "
                "Returns category name, total amount, transaction count, "
                "and average transaction amount."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Return only top N categories by spend",
                        "default": 5
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_monthly_trends",
            description=(
                "Get monthly transaction trends from the Gold layer. "
                "Shows credit vs debit totals and flagged counts per month."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_risk_summary",
            description=(
                "Get a summary of flagged transactions by risk type. "
                "Use this to understand the overall risk profile."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:

    supabase = get_supabase()

    if name == "get_spend_by_category":
        result = supabase.table("gold_spend_by_category").select("*").order(
            "total_amount", desc=True
        ).execute()

        data = result.data
        top_n = arguments.get("top_n", 5)
        data = data[:top_n]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "spend_by_category": data,
                "top_n": top_n
            }, indent=2)
        )]

    elif name == "get_monthly_trends":
        result = supabase.table("gold_monthly_trends").select("*").execute()

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "monthly_trends": result.data
            }, indent=2)
        )]

    elif name == "get_risk_summary":
        result = supabase.table("gold_flagged_summary").select("*").order(
            "total_amount", desc=True
        ).execute()

        total_flagged = sum(r["count"] for r in result.data)
        total_flagged_amount = sum(
            float(r["total_amount"]) for r in result.data
        )

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "total_flagged_transactions": total_flagged,
                "total_flagged_amount_aed": round(total_flagged_amount, 2),
                "by_type": result.data
            }, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())