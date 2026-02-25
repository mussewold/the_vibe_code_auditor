from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def pdf_parse(path: str) -> str:
    """
    Extract text from a PDF report.

    Prefers Docling when available; falls back to a very small PyPDF2-based
    extractor if installed. Raises a clear RuntimeError if no PDF backend
    is available so the caller can surface a useful error to the user.
    """

    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # --- Preferred: Docling ---
    try:
        from docling.document_converter import DocumentConverter  # type: ignore

        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))

        # Newer Docling APIs typically expose a text export; we keep this
        # generic so it degrades gracefully across minor version changes.
        if hasattr(result, "document") and hasattr(result.document, "export_to_text"):
            return result.document.export_to_text()

        if hasattr(result, "text"):
            return str(result.text)

    except Exception:
        # Swallow and fall back to a simpler extractor.
        pass

    # --- Fallback: PyPDF2 (if present) ---
    try:
        import PyPDF2  # type: ignore

        text_parts: List[str] = []
        with pdf_path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text() or ""
                text_parts.append(extracted)

        return "\n\n".join(text_parts)

    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "Unable to parse PDF. Install `docling` or `PyPDF2` to enable "
            "DocAnalyst PDF parsing."
        ) from exc


def markdown_read(path: str) -> str:
    """
    Read a Markdown / text file as a single string.
    """

    md_path = Path(path)
    if not md_path.exists():
        raise FileNotFoundError(f"Report not found: {md_path}")

    return md_path.read_text(encoding="utf-8")


def _split_into_paragraphs(text: str) -> List[str]:
    raw_parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw_parts if p.strip()]


def chunk_text(
    text: str,
    max_chars: int = 1200,
    overlap: int = 200,
) -> List[str]:
    """
    Very lightweight chunker for RAG-lite retrieval.

    - Starts from paragraphs, then packs them into overlapping character windows.
    - Overlap keeps important ideas visible across chunk boundaries.
    """

    paragraphs = _split_into_paragraphs(text)
    chunks: List[str] = []

    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current and current_len + para_len + 2 > max_chars:
            chunks.append("\n\n".join(current))

            # Build the overlapping prefix for the next chunk.
            if overlap > 0:
                overlap_text = "\n\n".join(current)[-overlap:]
                current = [overlap_text]
                current_len = len(overlap_text)
            else:
                current = []
                current_len = 0

        current.append(para)
        current_len += para_len + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def ingest_pdf(path: str) -> List[str]:
    """
    High-level ingest helper used by DocAnalyst.

    Decides how to read the report based on file extension and returns
    RAG-ready chunks.
    """

    report_path = Path(path)
    ext = report_path.suffix.lower()

    if ext == ".pdf":
        full_text = pdf_parse(str(report_path))
    else:
        full_text = markdown_read(str(report_path))

    return chunk_text(full_text)


def find_relevant_chunks(
    chunks: Sequence[str],
    query_terms: Sequence[str],
    top_k: int = 3,
) -> List[Tuple[int, str]]:
    """
    Score chunks by simple term frequency and return the top_k matches.
    """

    scores: List[Tuple[int, int]] = []  # (score, index)
    lowered_terms = [t.lower() for t in query_terms]

    for idx, chunk in enumerate(chunks):
        lc = chunk.lower()
        score = 0
        for term in lowered_terms:
            score += lc.count(term)

            # Light bonus if the term appears in a likely heading.
            if re.search(rf"^#+\s*{re.escape(term)}", chunk, flags=re.IGNORECASE | re.MULTILINE):
                score += 2

        if score > 0:
            scores.append((score, idx))

    # Sort by descending score, then by ascending index (stable order).
    scores.sort(key=lambda s: (-s[0], s[1]))

    top_indices = [idx for _, idx in scores[:top_k]]
    return [(i, chunks[i]) for i in top_indices]


def cross_reference(
    cited_path: str,
    repo_root: str | Path | None = None,
) -> Dict[str, str | bool]:
    """
    Simple filesystem-based citation cross-reference.

    Given a path cited inside the report (e.g. ``src/nodes/judges.py``),
    resolve it against the local repository root and report whether it exists.
    """

    root = Path(repo_root) if repo_root is not None else Path.cwd()
    resolved = (root / cited_path).resolve()

    return {
        "exists": resolved.exists(),
        "resolved_path": str(resolved),
    }


def extract_cited_paths(text: str) -> List[str]:
    """
    Pull out file-like paths that look like code references from the report.

    Targets things like:
      - src/....py
      - tests/....py
      - backticked references such as `src/nodes/judges.py`
    """

    pattern = r"(?:`|\"|')?((?:src|tests)/[^\s`'\"),]+?\.py)(?:`|\"|')?"
    matches = re.findall(pattern, text)
    # Preserve order while deduplicating.
    seen = set()
    result: List[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


@dataclass
class ConceptOccurrence:
    term: str
    window: str
    is_deep: bool


def _extract_window(text: str, start: int, end: int, radius: int = 350) -> str:
    center = (start + end) // 2
    left = max(0, center - radius)
    right = min(len(text), center + radius)
    snippet = text[left:right]
    return snippet.strip()


def analyze_concept_depth(text: str, term: str) -> Dict[str, object]:
    """
    Heuristic concept-depth analyzer for Protocol B.

    Classifies mentions of a term as shallow vs deep based on:
      - length of surrounding window
      - presence of implementation verbs / architecture language
    """

    flags = [
        "we implement",
        "we orchestrate",
        "we designed",
        "this architecture",
        "the graph",
        "the nodes",
        "the judges",
        "langgraph",
    ]

    pattern = re.compile(re.escape(term), flags=re.IGNORECASE)

    occurrences: List[ConceptOccurrence] = []
    for match in pattern.finditer(text):
        snippet = _extract_window(text, match.start(), match.end())
        snippet_lower = snippet.lower()

        long_enough = len(snippet) > 280
        has_impl_language = any(flag in snippet_lower for flag in flags)

        is_deep = long_enough or has_impl_language
        occurrences.append(
            ConceptOccurrence(
                term=term,
                window=snippet,
                is_deep=bool(is_deep),
            )
        )

    deep = [o for o in occurrences if o.is_deep]
    shallow = [o for o in occurrences if not o.is_deep]

    example_windows: List[str] = []
    for occ in (deep[:2] + shallow[:2]):
        example_windows.append(occ.window)

    return {
        "term": term,
        "occurrences": len(occurrences),
        "deep_explanations": len(deep),
        "shallow_mentions": len(shallow),
        "examples": example_windows,
    }

