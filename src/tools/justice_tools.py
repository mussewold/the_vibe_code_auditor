import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from src.state import Evidence


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def ollama_chat(
    *,
    model: str,
    prompt: str,
    host: str,
    timeout_s: float = 30.0,
) -> Optional[str]:
    """
    Minimal Ollama client via HTTP to avoid new dependencies.
    Returns model text, or None if Ollama isn't reachable / errors.
    """
    url = host.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    message = (data or {}).get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return content.strip() or None


def flatten_evidence_snippets(
    evidences: Dict[str, List[Evidence]],
    *,
    max_sources: int = 3,
    max_chars_per_source: int = 900,
) -> str:
    """
    Produce a compact, prosecution-friendly evidence excerpt block
    (to keep Ollama prompts bounded).
    """
    blocks: List[str] = []
    for source, ev_list in evidences.items():
        if not ev_list:
            continue
        snippet_lines: List[str] = []
        for ev in ev_list[:max_sources]:
            snippet_lines.append(f"- goal: {ev.goal}")
            snippet_lines.append(f"  found: {ev.found}")
            snippet_lines.append(f"  location: {ev.location}")
            snippet = truncate((ev.content or "").strip(), max_chars_per_source)
            if snippet:
                snippet_lines.append(f"  content: {snippet}")
        if snippet_lines:
            blocks.append(f"[{source}]\n" + "\n".join(snippet_lines))
    return "\n\n".join(blocks).strip()

