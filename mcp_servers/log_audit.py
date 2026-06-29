# mcp_servers/log_audit.py
# MCP Server 2: Write agent decisions to the audit log
# Every agent decision gets recorded here for governance

import os
import json
import uuid
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

server = Server("log-audit")

def get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="log_agent_decision",
            description=(
                "Log an agent's decision to the audit trail. "
                "Call this after every significant agent action "
                "to maintain a governance record."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Unique ID for this agent run"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent making this log entry"
                    },
                    "action": {
                        "type": "string",
                        "description": "What action the agent performed"
                    },
                    "input_summary": {
                        "type": "string",
                        "description": "Brief summary of what the agent received as input"
                    },
                    "output_summary": {
                        "type": "string",
                        "description": "Brief summary of what the agent produced"
                    },
                    "decision": {
                        "type": "string",
                        "description": "The actual decision made"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why the agent made this decision"
                    }
                },
                "required": [
                    "run_id",
                    "agent_name",
                    "action",
                    "decision"
                ]
            }
        ),
        types.Tool(
            name="get_audit_log",
            description="Retrieve audit log entries for a specific run ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "The run ID to retrieve logs for"
                    }
                },
                "required": ["run_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:

    supabase = get_supabase()

    if name == "log_agent_decision":
        record = {
            "id": str(uuid.uuid4()),
            "run_id": arguments["run_id"],
            "agent_name": arguments["agent_name"],
            "action": arguments["action"],
            "input_summary": arguments.get("input_summary", ""),
            "output_summary": arguments.get("output_summary", ""),
            "decision": arguments["decision"],
            "reasoning": arguments.get("reasoning", ""),
            "created_at": datetime.utcnow().isoformat()
        }

        supabase.table("audit_logs").insert(record).execute()

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "logged",
                "log_id": record["id"],
                "agent": arguments["agent_name"],
                "action": arguments["action"]
            }, indent=2)
        )]

    elif name == "get_audit_log":
        result = supabase.table("audit_logs").select("*").eq(
            "run_id", arguments["run_id"]
        ).order("created_at").execute()

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "run_id": arguments["run_id"],
                "entries": result.data
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