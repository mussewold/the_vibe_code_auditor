# The AI Court Room

A LangGraph-powered “AI court” that runs multiple detective and judge agents in parallel to forensically evaluate a target repository and its accompanying PDF report.

This README covers:
- Setup & installation
- How to install dependencies
- How to run the detective graph against a target repo URL and PDF report

---

## Prerequisites

- **Python 3.11+** (recommended to match LangGraph ecosystem)
- **git** (for cloning target repositories in the `RepoInvestigator` node)
- A virtual environment tool of your choice:
  - `python -m venv venv` (built‑in)
  - or `conda`, `uv`, etc.

---

## Setup & Installation

From the project root:

```bash
git clone <this-repo-url>
cd the_ai_court_room
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # on macOS / Linux
# .venv\Scripts\activate   # on Windows PowerShell
```

Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Optional but recommended**  
> If you want robust PDF parsing for `DocAnalyst`, also install:
>
> ```bash
> pip install docling PyPDF2
> ```

---

## Project Layout (High Level)

- `main.py` — CLI entry point for running the graph.
- `src/state.py` — shared `AgentState`, `Evidence`, and report models.
- `src/graph.py` — LangGraph `StateGraph` wiring for all nodes.
- `src/nodes/detectives.py` — detective agents:
  - `RepoInvestigator` — code / git forensics.
  - `DocAnalyst` — PDF report RAG‑lite analysis and citation checks.
  - `VisionInspector` — placeholder for rubric / image inspection.
- `src/nodes/judges.py` — judge agents (`Defense`, `Prosecutor`, `TechLead`, `ChiefJustice`).
- `src/tools/repo_tools.py` — AST & git utilities for `RepoInvestigator`.
- `src/tools/doc_tools.py` — PDF / markdown ingest, RAG‑lite chunking, and concept analysis helpers.

---

## Running the Detective Graph Against a Target Repo

The typical flow is:
1. Choose a **target repository URL** (e.g. a GitHub repo).
2. Obtain or generate a **PDF (or markdown) report** describing that repo’s architecture.
3. Run the AI Court Room graph with those inputs.

### 1. Prepare Inputs

- **Repository URL**
  - Example: `https://github.com/your-org/your-repo.git`
- **PDF report path**
  - Place your report somewhere accessible on disk (e.g. `reports/audit.pdf`), or use a markdown file (e.g. `reports/audit.md`) if you prefer.

`AgentState` expects:
- `repo_url`: the git clone URL for the target repository.
- `pdf_path`: absolute or repo‑relative path to the report file.

### 2. Run via `main.py`

If `main.py` already defines a CLI, the typical pattern is:

```bash
python -m main \
  --repo-url "https://github.com/your-org/your-repo.git" \
  --pdf-path "reports/audit.pdf"
```

If your entrypoint differs, adapt the command to however `AgentState` is constructed in `main.py`, ensuring at minimum:

- `state["repo_url"]` is set to the target git URL.
- `state["pdf_path"]` points at your report file.

The LangGraph is compiled in `src/graph.py` and orchestrates the following:

- `ContextBuilder` seeds initial context.
- `RepoInvestigator`, `DocAnalyst`, and `VisionInspector` run **in parallel**.
- `EvidenceAggregator` and the judge nodes consume `state.evidences` to produce a final audit report.

---

## What DocAnalyst & RepoInvestigator Do

- **RepoInvestigator**
  - Clones the target repo into a temporary sandbox.
  - Performs AST‑based analysis of `state.py`, `graph.py`, and the LangGraph wiring.
  - Builds a git narrative (commit history, development style).

- **DocAnalyst**
  - Ingests the PDF/markdown report via a RAG‑lite chunker.
  - Answers: **“What does the report say about Dialectical Synthesis?”** by retrieving relevant chunks.
  - **Forensic Protocol A (Citation Check)**:
    - Detects cited file paths like `src/nodes/judges.py`.
    - Cross‑references them against the actual repo filesystem and flags hallucinated paths.
  - **Forensic Protocol B (Concept Verification)**:
    - Checks whether **“Dialectical Synthesis”** and **“Metacognition”** are deeply explained (implementation‑level) or just name‑dropped.

All of this evidence flows into `state.evidences` and can be consumed by downstream judges to produce a final `AuditReport`.

---

## Troubleshooting

- **PDF parsing errors**
  - Ensure `docling` or `PyPDF2` is installed.
  - Confirm `pdf_path` points to a real file (absolute or relative to the project root).

- **Git clone errors**
  - Make sure `git` is installed and on your `PATH`.
  - Verify the repo URL is accessible (authentication / network).

If you run into issues wiring a different entrypoint or integrating this into another system, inspect `src/graph.py` and `src/nodes/detectives.py` to see exactly how `AgentState` is expected to be constructed and passed into the graph.

