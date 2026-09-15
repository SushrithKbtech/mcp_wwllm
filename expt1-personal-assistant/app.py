"""
Expt 1: Basic web UI for the Personal Assistant Memory Server.

Flask app that acts as the MCP client (persistent stdio session to
server.py) with GPT-4o-mini deciding which tool (save_note / search_notes /
list_notes / delete_note) to call for each message typed in the browser.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""
import asyncio
import json
import os
import sys
import threading

from flask import Flask, jsonify, render_template_string, request
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "gpt-4o-mini"
SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

app = Flask(__name__)
openai_client = OpenAI()


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


class MCPBridge:
    """Runs a persistent MCP ClientSession on a background event loop
    so a synchronous Flask app can call async MCP tools per-request."""

    def __init__(self, server_script: str):
        self.server_script = server_script
        self.loop = asyncio.new_event_loop()
        self.tools = None
        self.session: ClientSession | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=30)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())
        self.loop.run_forever()

    async def _connect(self):
        params = StdioServerParameters(command=sys.executable, args=[self.server_script])
        self._stdio_cm = stdio_client(params)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()
        mcp_tools = (await self.session.list_tools()).tools
        self.tools = mcp_tools_to_openai(mcp_tools)
        self._ready.set()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=60)

    async def call_tool(self, name: str, args: dict) -> str:
        result = await self.session.call_tool(name, args)
        return "\n".join(b.text for b in result.content if hasattr(b, "text"))


bridge = MCPBridge(SERVER_SCRIPT)


def chat_with_tools(user_query: str) -> dict:
    """Runs the GPT-4o-mini tool-calling loop, returning a step-by-step
    trace (for the UI's 'thought process' panel) plus the final answer."""
    steps = []
    messages = [{"role": "user", "content": user_query}]

    while True:
        response = openai_client.chat.completions.create(
            model=MODEL, messages=messages, tools=bridge.tools
        )
        msg = response.choices[0].message

        if msg.content:
            steps.append({"type": "reasoning", "text": msg.content.strip()})

        if not msg.tool_calls:
            return {"steps": steps, "final_answer": msg.content or ""}

        messages.append(msg.model_dump(exclude_unset=True))

        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            steps.append(
                {"type": "tool_call", "name": tool_call.function.name, "args": args}
            )
            result_text = bridge.run(bridge.call_tool(tool_call.function.name, args))
            steps.append({"type": "tool_result", "text": result_text})
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
            )


PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Personal Assistant</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; background: #fafafa; color: #222; }
    h1 { font-size: 1.4rem; }
    #chat-form { display: flex; gap: 8px; margin-bottom: 24px; }
    #query { flex: 1; padding: 10px; font-size: 1rem; }
    button { padding: 10px 16px; font-size: 1rem; cursor: pointer; }
    .step { padding: 8px 12px; margin: 6px 0; border-radius: 6px; font-size: 0.9rem; white-space: pre-wrap; }
    .reasoning { background: #eef; }
    .tool_call { background: #fff3cd; font-family: monospace; }
    .tool_result { background: #d4edda; font-family: monospace; }
    .final { background: #222; color: #fff; padding: 12px; border-radius: 6px; margin-top: 12px; }
    #notes { margin-top: 32px; }
    .note { padding: 8px; border-bottom: 1px solid #ddd; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>🧠 Personal Assistant (MCP + GPT-4o-mini + SQLite)</h1>
  <form id="chat-form">
    <input id="query" placeholder='e.g. "Remember the project deadline is Friday" or "What did I say about the deadline?"' autocomplete="off">
    <button type="submit">Send</button>
  </form>
  <div id="log"></div>
  <div id="notes">
    <h2>All notes</h2>
    <div id="notes-list">Loading…</div>
  </div>

<script>
const form = document.getElementById('chat-form');
const log = document.getElementById('log');

async function refreshNotes() {
  const res = await fetch('/api/notes');
  const data = await res.json();
  const el = document.getElementById('notes-list');
  el.innerHTML = data.notes.replace(/\\n/g, '<br>');
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = document.getElementById('query').value.trim();
  if (!query) return;
  log.innerHTML = '<div class="step reasoning">Thinking…</div>';
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query})
  });
  const data = await res.json();
  log.innerHTML = '';
  for (const step of data.steps) {
    const div = document.createElement('div');
    div.className = 'step ' + step.type;
    if (step.type === 'tool_call') {
      div.textContent = `🔧 calling ${step.name}(${JSON.stringify(step.args)})`;
    } else if (step.type === 'tool_result') {
      div.textContent = '📄 ' + step.text;
    } else {
      div.textContent = '💭 ' + step.text;
    }
    log.appendChild(div);
  }
  const finalDiv = document.createElement('div');
  finalDiv.className = 'final';
  finalDiv.textContent = data.final_answer;
  log.appendChild(finalDiv);
  document.getElementById('query').value = '';
  refreshNotes();
});

refreshNotes();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_query = request.json.get("query", "")
    result = chat_with_tools(user_query)
    return jsonify(result)


@app.route("/api/notes")
def api_notes():
    notes = bridge.run(bridge.call_tool("list_notes", {}))
    return jsonify({"notes": notes})


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: set the OPENAI_API_KEY environment variable first.")
        sys.exit(1)
    app.run(debug=False, port=5000)
