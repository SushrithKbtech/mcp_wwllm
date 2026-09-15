"""
Expt 1: MCP Client (CLI) for the Personal Assistant Memory Server.

Connects to server.py over stdio, lets the user type a natural-language
query, and uses GPT-4o-mini to decide whether to call save_note,
search_notes, list_notes, or delete_note.
"""
import asyncio
import json
import os
import sys

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "gpt-4o-mini"
SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


def mcp_tools_to_openai(mcp_tools) -> list:
    """Convert MCP tool definitions into OpenAI's function-calling tool schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]


async def run_query(session: ClientSession, client: OpenAI, tools, user_query: str):
    messages = [{"role": "user", "content": user_query}]

    while True:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools
        )
        msg = response.choices[0].message

        if msg.content:
            print(f"[assistant] {msg.content.strip()}")

        if not msg.tool_calls:
            break

        messages.append(msg.model_dump(exclude_unset=True))

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            print(f"[tool call] {tool_call.function.name}({args})")
            result = await session.call_tool(tool_call.function.name, args)
            result_text = "\n".join(
                b.text for b in result.content if hasattr(b, "text")
            )
            print(f"[tool result] {result_text}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text,
                }
            )


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: set the OPENAI_API_KEY environment variable first.")
        sys.exit(1)

    client = OpenAI()
    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            tools = mcp_tools_to_openai(mcp_tools)
            print(f"Connected. Available tools: {[t.name for t in mcp_tools]}\n")

            print("Type a note to save, or ask a question to search your notes.")
            print("Type 'quit' to exit.\n")

            while True:
                user_query = input("You: ").strip()
                if user_query.lower() in {"quit", "exit"}:
                    break
                if not user_query:
                    continue
                await run_query(session, client, tools, user_query)
                print()


if __name__ == "__main__":
    asyncio.run(main())
