#!/usr/bin/env python3
"""MCP server that exposes SKILL.md files as skills to a tool-using LLM.

Skills live in a directory, one subfolder per skill:

    <skills-dir>/<skill-name>/SKILL.md

A skill folder may contain additional files besides SKILL.md (for example
`references/` documents and `agents/` metadata). `get_skill` returns the
SKILL.md content plus any `agents/` file content, and `list_skill_files` /
`read_skill_file` let the LLM discover and read the other files on demand.

Run:

    uv run server.py --skills-dir skills
    uv run server.py --host 127.0.0.1 --port 8080 --skills-dir skills

Clients connect to http://<host>:<port>/mcp (MCP streamable HTTP).
"""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

# Preferred file name, plus a fallback for case-insensitive file systems.
SKILL_FILENAMES = ("SKILL.md", "skill.md")


class SkillStore:
    """Read-only view over a directory of <skill-name>/SKILL.md folders."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _skill_path(self, entry: Path) -> Path | None:
        for name in SKILL_FILENAMES:
            path = entry / name
            if path.is_file():
                return path
        return None

    def scan(self) -> dict[str, Path]:
        """Return {skill_name: SKILL.md path} for every skill under root."""
        skills: dict[str, Path] = {}
        for entry in sorted(self.root.iterdir()):
            if not entry.is_dir():
                continue
            path = self._skill_path(entry)
            if path is not None:
                skills[entry.name] = path
        return skills

    def skill_dir(self, name: str) -> Path | None:
        """Folder of the named skill, or None if the skill does not exist."""
        skills = self.scan()
        return skills[name].parent if name in skills else None

    def list_files(self, name: str) -> str | None:
        """Skill folder contents as a comma-separated list of relative POSIX paths.

        Excludes SKILL.md/skill.md and the agents/ subtree (both are already
        returned by get_skill). Returns None for an unknown skill.
        """
        base = self.skill_dir(name)
        if base is None:
            return None
        names = set(SKILL_FILENAMES)
        rels = [
            entry.relative_to(base).as_posix()
            for entry in sorted(base.rglob("*"))
            if entry.is_file()
        ]
        paths = [rel for rel in rels if Path(rel).name not in names and not rel.startswith("agents/")]
        return ", ".join(paths) or "(no files besides SKILL.md and agents/)"

    def agents(self, name: str) -> list[tuple[str, str]]:
        """(relative path, content) pairs for files under the skill's agents/."""
        base = self.skill_dir(name)
        if base is None:
            return []
        entries = base / "agents"
        if not entries.is_dir():
            return []
        files = [
            (p.relative_to(base).as_posix(), p.read_text(encoding="utf-8", errors="replace"))
            for p in sorted(entries.rglob("*"))
            if p.is_file()
        ]
        return files

    def read_file(self, name: str, rel: str) -> tuple[str | None, str | None]:
        """Content of a skill file addressed by path relative to the skill folder.

        Returns (content, None) on success, (None, error_message) when the
        skill or file is missing, the path escapes the skill folder, or the
        path is not a regular file.
        """
        base = self.skill_dir(name)
        if base is None:
            known = ", ".join(sorted(self.scan())) or "(none)"
            return None, f"Unknown skill {name!r}. Available skills: {known}"
        candidate = (base / rel).resolve()
        try:
            candidate.relative_to(base.resolve())
        except ValueError:
            return None, (
                f"Path {rel!r} escapes the skill folder. Give a path relative "
                "to the skill folder, e.g. 'references/base-en.txt'."
            )
        if not candidate.is_file():
            known = [
                p.relative_to(base).as_posix()
                for p in sorted(base.rglob("*"))
                if p.is_file()
            ]
            listing = ", ".join(known) or "(none)"
            return None, f"File not found in skill {name!r}: {rel!r}. Files: {listing}"
        return candidate.read_text(encoding="utf-8", errors="replace"), None

    def summary(self, path: Path) -> str:
        """One-line description for a skill.

        Preference order: a `description:` key in YAML frontmatter, the first
        non-empty line that is not a heading, then the first line overall.
        """
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.startswith("description:"):
                    value = line.split(":", 1)[1].strip().strip("\"'")
                    if value:
                        return value
        fallback = ""
        for line in lines:
            line = line.strip()
            if not line or line.startswith("---"):
                continue
            if not fallback:
                fallback = line.lstrip("#").strip() or line
            if not line.startswith("#"):
                return line
        return fallback or "(no description)"


def build_server(skills_dir: Path) -> MCPServer:
    store = SkillStore(skills_dir.resolve())

    mcp = MCPServer(
        "skill-server",
        description="Serves SKILL.md skill documents to tool-using LLMs.",
        instructions=(
            "Use list_skills to see what is available, then call "
            "get_skill(name) to read a skill's full instructions (SKILL.md "
            "plus any agents/ metadata). Skills may reference other files in "
            "their folder; use list_skill_files(name) to see them and "
            "read_skill_file(name, path) to open one by its path relative to "
            "the skill folder, e.g. 'references/base-en.txt'."
        ),
    )

    @mcp.tool()
    def list_skills() -> dict[str, str]:
        """List available skills as a mapping of skill name to one-line description."""
        return {name: store.summary(path) for name, path in store.scan().items()}

    @mcp.tool()
    def get_skill(name: str) -> str:
        """Return the full instructions of a skill by name.

        Returns the skill's SKILL.md content, followed by the content of
        every file in the skill's agents/ folder (agent metadata such as
        display name and default prompts). Use list_skill_files to discover
        and read_skill_file to read the skill's other files.
        """
        skills = store.scan()
        path = skills.get(name)
        if path is None:
            known = ", ".join(sorted(skills)) or "(none)"
            raise ToolError(f"Unknown skill {name!r}. Available skills: {known}")
        parts = [path.read_text(encoding="utf-8", errors="replace")]
        for rel, content in store.agents(name):
            parts.append(f"\n\n--- {rel} ---\n\n{content}")
        return "".join(parts)

    @mcp.tool()
    def list_skill_files(name: str) -> str:
        """List the files of a skill (relative to the skill folder).

        SKILL.md and agents/ files are omitted because get_skill already
        returns them.
        """
        listing = store.list_files(name)
        if listing is None:
            known = ", ".join(sorted(store.scan())) or "(none)"
            raise ToolError(f"Unknown skill {name!r}. Available skills: {known}")
        return listing

    @mcp.tool()
    def read_skill_file(name: str, path: str) -> str:
        """Read a file of a skill, addressed by its path relative to the skill folder.

        Example: read_skill_file("h3-prompt-writing", "references/base-en.txt").
        Use list_skill_files to see the available paths.
        """
        content, error = store.read_file(name, path)
        if error is not None:
            raise ToolError(error)
        return content

    return mcp


def serve(mcp: MCPServer, host: str, port: int) -> None:
    """Serve the MCP app over streamable HTTP with CORS enabled.

    Browser-based MCP clients (e.g. the llama.cpp web UI) connect
    cross-origin and issue an OPTIONS preflight before their real
    requests. The plain app built by `mcp.run()` has no CORS middleware
    and answers the preflight with 405, so the browser aborts with a
    NetworkError. We wrap the app in CORSMiddleware so the preflight
    succeeds and the session headers are exposed to the browser.
    """
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[Mount("/", app=mcp_app)],
        lifespan=lifespan,
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],  # local tool server, no credentials
                allow_methods=["GET", "POST", "DELETE"],
                allow_headers=[
                    "Authorization",
                    "Content-Type",
                    "Last-Event-ID",
                    "Mcp-Method",
                    "Mcp-Name",
                    "Mcp-Protocol-Version",
                    "Mcp-Session-Id",
                ],
                expose_headers=["Mcp-Session-Id"],
            )
        ],
    )
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP server that serves SKILL.md skills over streamable HTTP."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host address to listen on (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        required=True,
        help="Directory containing <skill-name>/SKILL.md folders",
    )
    args = parser.parse_args()

    if not args.skills_dir.is_dir():
        parser.error(f"skills directory does not exist: {args.skills_dir}")

    serve(build_server(args.skills_dir), args.host, args.port)


if __name__ == "__main__":
    main()
