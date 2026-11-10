# skill-mcp

A small, lightweight MCP (Model Context Protocol) server in Python that serves
`SKILL.md` skill documents to a tool-capable LLM.

It exposes two tools:

| Tool | Description |
| ---- | ----------- |
| `list_skills` | Returns a mapping of available skill name → one-line description. |
| `get_skill(name)` | Returns the full `SKILL.md` content of a skill by name. |

## Layout

Skills are organized as one subfolder per skill:

```
<skills-dir>/
  code-review/
    SKILL.md
  git-workflow/
    SKILL.md
```

A skill is a folder that contains a `SKILL.md` file (a lowercase `skill.md` is
also accepted on case-insensitive file systems). Any other file or folder is
ignored.

## Install

[uv](https://docs.astral.sh/uv/) is used to run the server in an isolated
virtualenv. One dependency is required: the official [`mcp`](https://pypi.org/project/mcp/)
Python SDK (v2), which brings its usual transitive deps.

```sh
uv sync          # create .venv and install mcp
```

## Run

```sh
uv run server.py --skills-dir skills
```

CLI parameters:

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `--host <IP>` | Host address to listen on | `127.0.0.1` |
| `--port <PORT>` | Port to listen on | `8080` |
| `--skills-dir <DIR>` | Directory of `<skill-name>/SKILL.md` folders | *(required)* |

Example:

```sh
uv run server.py --host 127.0.0.1 --port 8080 --skills-dir skills
```

The server speaks MCP over **streamable HTTP** and serves the endpoint at
`/mcp`.

## Connect an MCP client

Point any MCP client at:

```
http://127.0.0.1:8080/mcp
```

The server sends CORS headers (`Access-Control-Allow-Origin: *`) and exposes
`Mcp-Session-Id`, so **browser-based clients** (e.g. the llama.cpp web UI,
which connects cross-origin from its own port) work out of the box. The
`OPTIONS` preflight is answered and the real `POST`/`GET`/`DELETE` calls are
granted. curl/Node clients work too — they simply skip the preflight.

Example client config (Claude Desktop / Claude Code style):

```json
{
  "mcpServers": {
    "skill-server": {
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

### Try it

```sh
uv run server.py -- --skills-dir skills
```

This launches the MCP Inspector in a browser; pick `list_skills` or
`get_skill` under the **Tools** tab. (`mcp dev` needs `npx` on `PATH`.)

## Notes

- Skills are read fresh on every call, so you can add, edit, or remove skill
  folders while the server is running — no restart needed.
- Unknown skill names return an error listing the available skills.
- The server binds `127.0.0.1` by default (localhost only). Pass `--host` to
  reach it from elsewhere; there is no authentication, so keep that in mind.
