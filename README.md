# skill-mcp

A small, lightweight MCP (Model Context Protocol) server in Python that serves
`SKILL.md` skill documents to a tool-capable LLM.

It exposes four tools:

| Tool | Description |
| ---- | ----------- |
| `list_skills` | Returns a mapping of available skill name → one-line description. |
| `get_skill(name)` | Returns the skill's `SKILL.md` content, plus the content of every file in the skill's `agents/` folder. |
| `list_skill_files(name)` | Lists the skill's other files as paths relative to the skill folder (`SKILL.md` and `agents/` are omitted — `get_skill` already returns them). |
| `read_skill_file(name, path)` | Reads one skill file by path relative to the skill folder, e.g. `references/base-en.txt`. |

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
also accepted on case-insensitive file systems). Files besides `SKILL.md`
(such as `references/` documents or `agents/` metadata) are served to the LLM
through `list_skill_files` / `read_skill_file`, and files under `agents/` are
inlined into the `get_skill` result.

Example skill with support files:

```
<skills-dir>/
  h3-prompt-writing/
    SKILL.md
    agents/
      openai.yaml
    references/
      base-en.txt
      ref-en.txt
```

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

In one terminal, start the server:

```sh
uv run server.py --skills-dir skills
```

In another, open the [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
pointed at the streamable HTTP endpoint:

```sh
npx @modelcontextprotocol/inspector --transport http --server-url http://127.0.0.1:8080/mcp
```

The Inspector's web UI opens in a browser; pick `list_skills`, `get_skill`,
`list_skill_files`, or `read_skill_file` under the **Tools** tab and run it.
(`npx` needs to be on `PATH`.)

## Notes

- Skills are read fresh on every call, so you can add, edit, or remove skill
  folders while the server is running — no restart needed.
- Unknown skill names return an error listing the available skills.
- `read_skill_file` is scoped to the named skill's folder: paths must be
  relative to it (e.g. `references/base-en.txt`), and anything that would
  escape the folder (e.g. `../other-skill/SKILL.md`) is rejected.
- The server binds `127.0.0.1` by default (localhost only). Pass `--host` to
  reach it from elsewhere; there is no authentication, so keep that in mind.
