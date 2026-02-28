# ⚖️ The AI Court Room

### A Multi-Agent LangGraph Auditor with Deterministic Judicial Synthesis

> A production-grade, rubric-driven repository auditor built on
> LangGraph, featuring parallel Detectives, adversarial Judges, and a
> deterministic Chief Justice synthesis engine.

---

## 🧠 Overview

**The AI Court Room** is a structured, forensic evaluation system that
audits:

- A GitHub repository
- A corresponding PDF architectural report
- Associated architecture diagrams

It implements:

- AST-based repository analysis (no regex shortcuts)
- Git forensic timeline inspection
- RAG-lite document cross-reference
- Parallel adversarial judge personas
- Deterministic Chief Justice conflict resolution
- Typed state with reducer-safe parallel execution

This is not a single LLM grader.

It is a **multi-agent judicial system** with enforced structure and
synthesis rules.

---

# 🏗 Architecture Overview

START\
↓\
ContextBuilder\
↓\
Detectives (Parallel): RepoInvestigator \| DocAnalyst \|
VisionInspector\
↓\
EvidenceAggregator\
↓\
Judges (Parallel): Prosecutor \| Defense \| TechLead\
↓\
ChiefJustice (Deterministic Rules Engine)\
↓\
END → Markdown Audit Report

---

# 🔬 Core Design Principles

## 1️⃣ Strict State Management

- AgentState is a TypedDict\
- Evidence, JudicialOpinion, and AuditReport are Pydantic BaseModel\
- Uses reducers:
  - operator.add for parallel list accumulation
  - operator.ior for dict merging

Prevents parallel agent overwrites.

---

## 2️⃣ AST-Based Repository Analysis

The RepoInvestigator:

- Clones the repo in a sandbox
- Uses AST parsing (not regex)
- Extracts commit history safely
- Detects bulk upload patterns vs iterative development

---

## 3️⃣ RAG-Lite Document Forensics

The DocAnalyst:

- Parses PDF or Markdown
- Chunks text for concept retrieval
- Cross-references cited paths
- Flags hallucinated files
- Detects keyword dropping without explanation

---

## 4️⃣ Adversarial Judge Personas

Judge Philosophy

---

Prosecutor Trust No One
Defense Reward Effort
TechLead Does it actually work?

Structured JudicialOpinion output includes:

- judge
- criterion_id
- score (1--5)
- argument
- cited_evidence

---

## 5️⃣ Deterministic Chief Justice Engine

Not an averaging LLM.

Enforces:

- Security Override Rule\
- Fact Supremacy Rule\
- Functionality Weight Rule\
- Variance Re-Evaluation Rule\
- Mandatory Dissent Summary Rule

Outputs:

- Executive Summary\
- Criterion Breakdown\
- Dissents\
- Remediation Plan\
- Final Structured Markdown Report

---

# 🚀 Installation (Using uv)

```bash
git clone <your-repo-url>
cd the-ai-court-room
uv sync
```

---

# ▶ Running the Auditor

```bash
uv run main.py   --repo-url "https://github.com/your-org/your-repo.git"   --pdf-path "reports/architecture.pdf"
```

---

# 🐳 Docker

```bash
docker build -t ai-court-room .
docker run --rm -e OPENAI_API_KEY=your_key ai-court-room   uv run main.py --repo-url "<repo>" --pdf-path "<pdf>"
```

---

# 🔐 Environment Variables

Create `.env`:

OPENAI_API_KEY=your_openai_api_key_here\
GITHUB_TOKEN=your_github_token_here\
LANGCHAIN_API_KEY=optional

---

# 🧪 Testing

```bash
pytest
```

---

# 📜 Output

- Structured AuditReport object\
- Rendered Markdown audit\
- SQLite checkpoint history\
- Saved file: audit/audit_report.md

---

# 🏛 Why This Project Is Architecturally Serious

Demonstrates:

- Typed state management\
- Parallel LangGraph orchestration\
- AST-based repo inspection\
- Deterministic rule-based synthesis\
- Structured LLM output enforcement\
- Multi-agent adversarial reasoning

This is system engineering --- not prompt engineering.

---
