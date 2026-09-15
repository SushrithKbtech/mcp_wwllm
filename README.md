# AI Coding Assistant MCP Experiments

Two experiments demonstrating the Model Context Protocol (MCP): a client
connects to a local MCP server over stdio, and GPT-4o-mini decides which
server-exposed tool to call based on the user's natural-language query.
Each experiment ships both a CLI client and a basic local web UI.

## Expt 1 — The "Personal Assistant" Memory Server

`expt1-personal-assistant/`

- **Server** (`server.py`): exposes CRUD tools — `save_note(content, tags)`,
  `search_notes(query)`, `list_notes()`, `delete_note(note_id)`. Notes
  persist to a local SQLite database (`notes.db`).
- **Client** (`client.py`): a CLI where you type a query (e.g. "Remind me
  the project deadline is Friday" or "What did I say about the deadline?")
  and GPT-4o-mini decides which tool to call.
- **Web UI** (`app.py`): a basic Flask page (http://127.0.0.1:5000) with a
  chat box that shows the LLM's reasoning, tool calls, and tool results,
  plus a live list of all saved notes.

## Expt 2 — The "Data Dashboard" Connector

`expt2-data-dashboard/`

- **Server** (`server.py`): exposes `get_current_weather(location)`,
  fetching live data from the free [wttr.in](https://wttr.in) API.
- **Client** (`client.py`): a CLI that shows GPT-4o-mini's "thought
  process" (deciding to call the tool, the raw tool result) before
  printing the final summarized answer.
- **Web UI** (`app.py`): a basic Flask page (http://127.0.0.1:5001) with a
  chat box showing the same reasoning → tool call → tool result → final
  answer trace.

## Setup

Each experiment has its own `requirements.txt`. From inside an experiment
folder:

```bash
pip install -r requirements.txt
```

Both clients/UIs require an OpenAI API key (GPT-4o-mini):

```bash
export OPENAI_API_KEY=sk-...
```

(On Windows PowerShell: `$env:OPENAI_API_KEY = "sk-..."`)

## Running

CLI:

```bash
cd expt1-personal-assistant
python client.py
```

```bash
cd expt2-data-dashboard
python client.py
```

Web UI:

```bash
cd expt1-personal-assistant
python app.py        # open http://127.0.0.1:5000
```

```bash
cd expt2-data-dashboard
python app.py         # open http://127.0.0.1:5001
```

The client/app spawns the corresponding `server.py` as a subprocess over
stdio automatically — no need to run the server separately. This is a
local-only setup (no public deployment); for course submission, run it
locally and take screenshots.
