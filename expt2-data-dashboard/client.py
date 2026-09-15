"""
Expt 2: MCP Client (CLI) for the Data Dashboard Connector.

A simple CLI: the user asks "What's the weather in Tokyo?", and the app
shows GPT-4o-mini's "thought process" (deciding to call the tool) before
displaying the final, summarized answer.
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

SEP = "-" * 60


def mcp_tools_to_openai(mcp_tools) -> list:
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


async def ask(session: ClientSession, client: OpenAI, tools, user_query: str):
    messages = [{"role": "user", "content": user_query}]

    print(SEP)
    print("STEP 1 — Sending query to GPT-4o-mini with available tools...")
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    msg = response.choices[0].message

    if msg.content:
        print(f"[GPT-4o-mini's reasoning] {msg.content.strip()}")

    if not msg.tool_calls:
        print(SEP)
        print("FINAL ANSWER:")
        print(msg.content)
        return

    messages.append(msg.model_dump(exclude_unset=True))

    print(SEP)
    print("STEP 2 — GPT-4o-mini decided to call a tool:")
    for tool_call in msg.tool_calls:
        args = json.loads(tool_call.function.arguments or "{}")
        print(f"  -> calling {tool_call.function.name}({args})")
        result = await session.call_tool(tool_call.function.name, args)
        result_text = "\n".join(b.text for b in result.content if hasattr(b, "text"))
        print(f"  <- tool returned:\n{result_text}")
        messages.append(
            {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
        )

    print(SEP)
    print("STEP 3 — Sending tool result back to GPT-4o-mini for a final summary...")
    final = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)

    print(SEP)
    print("FINAL ANSWER:")
    print(final.choices[0].message.content)


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

            print("Ask about the weather anywhere, e.g. \"What's the weather in Tokyo?\"")
            print("Type 'quit' to exit.\n")

            while True:
                user_query = input("You: ").strip()
                if user_query.lower() in {"quit", "exit"}:
                    break
                if not user_query:
                    continue
                await ask(session, client, tools, user_query)
                print()


if __name__ == "__main__":
    asyncio.run(main())
