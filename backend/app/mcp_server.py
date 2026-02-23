"""PaperRadar MCP Server — Expose PaperRadar to Claude/Cursor via MCP protocol.

Usage:
  pip install fastmcp
  python -m app.mcp_server

Or add to Claude Desktop / Cursor MCP config:
  {
    "mcpServers": {
      "paperradar": {
        "command": "python",
        "args": ["-m", "app.mcp_server"],
        "cwd": "/path/to/backend"
      }
    }
  }
"""

from __future__ import annotations

import json
import httpx
from fastmcp import FastMCP

# PaperRadar API base URL (local container)
API_BASE = "http://localhost:9200"

mcp = FastMCP("PaperRadar", description="Search, analyze, and chat with academic papers")


def _api(method: str, path: str, **kwargs) -> dict:
    with httpx.Client(base_url=API_BASE, timeout=60.0) as client:
        resp = getattr(client, method)(path, **kwargs)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def search_papers(query: str, n: int = 5) -> str:
    """Semantic search across all papers in the knowledge base. Returns matching text chunks with relevance scores."""
    data = _api("get", f"/api/knowledge/search?q={query}&n={n}")
    results = data.get("results", [])
    lines = [f"Found {len(results)} results for '{query}':\n"]
    for r in results:
        lines.append(f"  [{r['score']:.0%}] ({r['metadata'].get('type','')}) {r['text'][:200]}")
    return "\n".join(lines)


@mcp.tool()
def list_papers() -> str:
    """List all papers in the knowledge base with their extraction status."""
    papers = _api("get", "/api/knowledge/papers")
    lines = [f"Knowledge base: {len(papers)} papers\n"]
    for p in papers:
        lines.append(f"  [{p['extraction_status']}] {p['title'][:80]} (id: {p['id']})")
    return "\n".join(lines)


@mcp.tool()
def get_paper(paper_id: str) -> str:
    """Get detailed knowledge from a specific paper including entities, findings, methods."""
    data = _api("get", f"/api/knowledge/papers/{paper_id}")
    meta = data.get("metadata", {})
    title = meta.get("title", "")
    if isinstance(title, dict):
        title = title.get("en", "")
    lines = [f"Paper: {title}\n"]
    lines.append(f"Entities: {len(data.get('entities', []))}")
    lines.append(f"Findings: {len(data.get('findings', []))}")
    lines.append(f"Methods: {len(data.get('methods', []))}")
    for f in data.get("findings", [])[:5]:
        stmt = f.get("statement", "")
        if isinstance(stmt, dict):
            stmt = stmt.get("en", "")
        lines.append(f"  [{f.get('type','')}] {stmt[:150]}")
    return "\n".join(lines)


@mcp.tool()
def chat_with_papers(question: str) -> str:
    """Ask a question across all papers in the knowledge base. Uses RAG for best results."""
    data = _api("post", "/api/knowledge/chat", json={"message": question})
    return data.get("reply", "No response")


@mcp.tool()
def get_trending(days: int = 7) -> str:
    """Get trending AI/ML papers from HuggingFace over the last N days, sorted by community upvotes."""
    data = _api("get", f"/api/radar/trending?days={days}")
    papers = data.get("papers", [])
    lines = [f"Trending papers ({days}d): {len(papers)} papers\n"]
    for p in papers[:10]:
        lines.append(f"  ⬆{p.get('upvotes',0):3} {p['title'][:80]}")
    return "\n".join(lines)


@mcp.tool()
def radar_status() -> str:
    """Get the current status of the paper radar engine."""
    data = _api("get", "/api/radar/status")
    return json.dumps(data, indent=2)


@mcp.tool()
def process_arxiv_paper(arxiv_id: str) -> str:
    """Download and process an arXiv paper by ID (e.g. '2401.12345'). Translates, highlights, and extracts knowledge."""
    data = _api("post", "/api/upload-url", json={"url": arxiv_id, "mode": "translate", "highlight": True})
    return f"Processing started. Task ID: {data.get('task_id', 'unknown')}, arXiv: {data.get('arxiv_id', arxiv_id)}"


@mcp.tool()
def generate_literature_review(topic: str = "") -> str:
    """Generate a structured literature review from all papers in the knowledge base."""
    data = _api("post", "/api/knowledge/review/generate", json={"topic": topic})
    return data.get("review", "No review generated")


if __name__ == "__main__":
    mcp.run()
