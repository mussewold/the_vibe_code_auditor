from typing import Dict, List
from pathlib import Path

from src.state import AgentState, Evidence
from src.tools.repo_tools import (
    analyze_state_structure,
    clone_repo_sandbox,
    extract_git_history,
)
from src.tools.doc_tools import (
    analyze_concept_depth,
    cross_reference,
    extract_cited_paths,
    find_relevant_chunks,
    ingest_pdf,
    markdown_read,
    pdf_parse,
)


def _summarize_repo_forensics(
    graph_findings: Dict,
    history: Dict,
) -> str:
    """
    Human-readable forensic narrative aligned with
    Protocol A (State), Protocol B (Graph Wiring),
    Protocol C (Git Narrative).
    """

    lines: List[str] = []
    lines.append("Repository Forensic Summary")

    # ------------------------------------------------------
    # Protocol A — State Structure
    # ------------------------------------------------------
    lines.append("\n[Protocol A — State Structure]")

    if graph_findings.get("state_files_found"):
        lines.append("- state.py / graph.py: present")
    else:
        lines.append("- state.py / graph.py: NOT found")

    if graph_findings.get("typed_state_detected"):
        lines.append("- Typed state schema: detected")
    else:
        lines.append("- Typed state schema: NOT detected")

    if graph_findings.get("operator_add_detected"):
        lines.append("- operator.add reducer: detected")
    if graph_findings.get("operator_ior_detected"):
        lines.append("- operator.ior reducer: detected")
    if graph_findings.get("annotated_detected"):
        lines.append("- Annotated type hint: detected")

    # ------------------------------------------------------
    # Protocol B — Graph Wiring
    # ------------------------------------------------------
    lines.append("\n[Protocol B — Graph Wiring]")

    if graph_findings.get("stategraph_detected"):
        lines.append("- StateGraph instantiation: detected")
    else:
        lines.append("- StateGraph instantiation: NOT detected")

    edges = graph_findings.get("edges", []) or []

    if edges:
        lines.append("- Graph edges:")
        for src, dst in edges:
            lines.append(f"  • {src} → {dst}")
    else:
        lines.append("- No edges discovered")

    if graph_findings.get("fan_out_detected"):
        lines.append("- Parallel fan-out architecture: detected ✅")
    else:
        lines.append("- Parallel fan-out architecture: NOT detected ❌")

    # ------------------------------------------------------
    # Protocol C — Git Narrative
    # ------------------------------------------------------
    lines.append("\n[Protocol C — Git Narrative]")

    if history.get("errors"):
        lines.append(f"- Git analysis error: {history['errors']}")
    else:
        lines.append(f"- Commit count: {history.get('commit_count', 0)}")
        lines.append(
            f"- Development style: {history.get('development_style')}"
        )

        commits = history.get("commits", [])[:5]

        if commits:
            lines.append("- Early commit timeline:")
            for c in commits:
                lines.append(
                    f"  • {c['hash']} @ {c['timestamp']} — {c['message']}"
                )

    return "\n".join(lines)


def repo_investigator_node(state: AgentState) -> AgentState:
    """
    RepoInvestigator — The Code Detective

    Executes:
    - sandbox clone
    - Protocol A/B AST investigation
    - Protocol C git narrative analysis
    """

    repo_url = state.get("repo_url", "")

    evidences = state.get("evidences", {}) or {}
    repo_evidence_list: List[Evidence] = evidences.get(
        "RepoInvestigator", []
    )

    # ------------------------------------------------------
    # Missing repo URL
    # ------------------------------------------------------
    if not repo_url:
        repo_evidence_list.append(
            Evidence(
                goal="Repository URL provided",
                found=False,
                content=None,
                location="n/a",
                rationale="No repository URL supplied.",
                confidence=0.2,
            )
        )
        return {"evidences": {"RepoInvestigator": repo_evidence_list}}

    # ------------------------------------------------------
    # Sandbox clone
    # ------------------------------------------------------
    try:
        local_repo_path = clone_repo_sandbox(repo_url)
    except Exception as e:
        repo_evidence_list.append(
            Evidence(
                goal="Repository cloned safely",
                found=False,
                content=str(e),
                location=repo_url,
                rationale="Clone failed (authentication/network).",
                confidence=0.4,
            )
        )
        return {"evidences": {"RepoInvestigator": repo_evidence_list}}

    # ------------------------------------------------------
    # Forensic protocols
    # ------------------------------------------------------
    graph_findings = analyze_state_structure(local_repo_path)
    history = extract_git_history(local_repo_path)

    summary = _summarize_repo_forensics(
        graph_findings=graph_findings,
        history=history,
    )

    # Success condition aligned with rubric:
    # must prove graph + typed state + git readable
    success = (
        graph_findings.get("stategraph_detected")
        and graph_findings.get("typed_state_detected")
        and not history.get("errors")
    )

    repo_evidence_list.append(
        Evidence(
            goal="Repository passes forensic LangGraph validation",
            found=bool(success),
            content=summary,
            location=local_repo_path,
            rationale=(
                "Repository analyzed using AST structural inspection "
                "and git forensic narrative without regex reliance."
            ),
            confidence=0.85 if success else 0.6,
        )
    )

    return {"evidences": {"RepoInvestigator": repo_evidence_list}}

def doc_analyst_node(state: AgentState) -> AgentState:
    """
    DocAnalyst — The Paperwork / Context Detective

    Executes a lightweight RAG-style analysis over the PDF report:
    - Ingests and chunks the report.
    - Protocol A: checks that cited file paths actually exist in the repo.
    - Protocol B: verifies depth of treatment for key concepts.
    - Answers: "What does the report say about Dialectical Synthesis?"
    """

    evidences = state.get("evidences", {}) or {}
    doc_evidence_list: List[Evidence] = evidences.get("DocAnalyst", [])

    pdf_path = state.get("pdf_path", "")
    if not pdf_path:
        doc_evidence_list.append(
            Evidence(
                goal="PDF report provided",
                found=False,
                content=None,
                location="n/a",
                rationale="No pdf_path supplied in AgentState.",
                confidence=0.2,
            )
        )
        return {"evidences": {"DocAnalyst": doc_evidence_list}}

    report_path = Path(pdf_path)

    if not report_path.exists():
        doc_evidence_list.append(
            Evidence(
                goal="PDF report exists on disk",
                found=False,
                content=None,
                location=str(report_path),
                rationale="pdf_path is set but the file does not exist.",
                confidence=0.3,
            )
        )
        return {"evidences": {"DocAnalyst": doc_evidence_list}}

    # ------------------------------------------------------
    # Load full text + RAG-lite chunks
    # ------------------------------------------------------
    try:
        if report_path.suffix.lower() == ".pdf":
            full_text = pdf_parse(str(report_path))
        else:
            full_text = markdown_read(str(report_path))
    except Exception as e:
        doc_evidence_list.append(
            Evidence(
                goal="PDF report successfully parsed",
                found=False,
                content=str(e),
                location=str(report_path),
                rationale=(
                    "Failed to parse report using available backends "
                    "(Docling / PyPDF2 / text reader)."
                ),
                confidence=0.3,
            )
        )
        return {"evidences": {"DocAnalyst": doc_evidence_list}}

    chunks = ingest_pdf(str(report_path))

    # ------------------------------------------------------
    # Protocol A — Citation Check
    # ------------------------------------------------------
    cited_paths = extract_cited_paths(full_text)

    citation_lines: List[str] = []
    missing_any = False

    if not cited_paths:
        citation_lines.append("No explicit src/... or tests/... Python paths cited.")
    else:
        citation_lines.append("Cited file paths discovered in report:")
        for cited in cited_paths:
            ref = cross_reference(cited)
            exists = bool(ref.get("exists"))
            resolved_path = ref.get("resolved_path", "")

            status = "OK" if exists else "Hallucination — missing on disk"
            if not exists:
                missing_any = True

            citation_lines.append(f"- {cited}  →  {status} ({resolved_path})")

    doc_evidence_list.append(
        Evidence(
            goal="Protocol A — Report citations match repository structure",
            found=not missing_any,
            content="\n".join(citation_lines),
            location=str(report_path),
            rationale=(
                "Scanned the report for src/... and tests/... Python paths and "
                "cross-referenced them against the local filesystem. Any cited "
                "file that does not exist is flagged as a hallucination."
            ),
            confidence=0.85,
        )
    )

    # ------------------------------------------------------
    # Protocol B — Concept Verification
    # ------------------------------------------------------
    ds_stats = analyze_concept_depth(full_text, "Dialectical Synthesis")
    meta_stats = analyze_concept_depth(full_text, "Metacognition")

    def _summarize_term(stats: Dict[str, object]) -> str:
        term = stats.get("term", "")
        occurrences = stats.get("occurrences", 0)
        deep = stats.get("deep_explanations", 0)
        shallow = stats.get("shallow_mentions", 0)
        examples = stats.get("examples", []) or []

        lines: List[str] = []
        lines.append(f"Term: {term}")
        lines.append(f"- Occurrences: {occurrences}")
        lines.append(f"- Deep explanations: {deep}")
        lines.append(f"- Shallow mentions: {shallow}")
        if examples:
            lines.append("- Representative excerpts:")
            for i, ex in enumerate(examples, start=1):
                lines.append(f"  ({i}) {ex.strip()}")
        return "\n".join(lines)

    concept_lines: List[str] = []
    concept_lines.append(_summarize_term(ds_stats))
    concept_lines.append("")
    concept_lines.append(_summarize_term(meta_stats))

    deep_enough = bool(ds_stats.get("deep_explanations")) and bool(
        meta_stats.get("deep_explanations")
    )

    doc_evidence_list.append(
        Evidence(
            goal="Protocol B — Deep treatment of Dialectical Synthesis and Metacognition",
            found=deep_enough,
            content="\n".join(concept_lines),
            location=str(report_path),
            rationale=(
                "Classified mentions of each concept as shallow vs deep based on "
                "surrounding context length and implementation-oriented language. "
                "Credit is given only when the report appears to operationalize "
                "the concepts in the system architecture."
            ),
            confidence=0.7,
        )
    )

    # ------------------------------------------------------
    # RAG-lite answer: Dialectical Synthesis
    # ------------------------------------------------------
    relevant = find_relevant_chunks(chunks, ["Dialectical Synthesis"])

    if not relevant:
        doc_evidence_list.append(
            Evidence(
                goal="Answer: What does the report say about Dialectical Synthesis?",
                found=False,
                content=None,
                location=str(report_path),
                rationale=(
                    "No chunks mentioning 'Dialectical Synthesis' were found in "
                    "the report during retrieval."
                ),
                confidence=0.4,
            )
        )
    else:
        lines: List[str] = []
        lines.append(
            "Below are direct excerpts from the report near mentions of "
            "'Dialectical Synthesis'. These are retrieved chunks, not "
            "rephrased summaries:"
        )
        for idx, chunk in relevant:
            lines.append("")
            lines.append(f"[Chunk {idx}]")
            lines.append(chunk.strip())

        doc_evidence_list.append(
            Evidence(
                goal="Answer: What does the report say about Dialectical Synthesis?",
                found=True,
                content="\n".join(lines),
                location=str(report_path),
                rationale=(
                    "Constructed an answer by retrieving the most relevant "
                    "chunks mentioning 'Dialectical Synthesis' from the report, "
                    "avoiding additional abstraction to reduce hallucination risk."
                ),
            confidence=0.8,
            )
        )

    return {"evidences": {"DocAnalyst": doc_evidence_list}}

def vision_inspector_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs rubric analysis:

    - Extracts the rubric's dimensions.
    - Extracts the rubric's criteria.
    - Extracts the rubric's scoring.
    """
    from src.tools.vision_tools import extract_images_from_pdf, analyze_diagram_with_llm

    pdf_path = state.get("pdf_path", "")
    evidences = state.get("evidences", {}) or {}
    vision_evidence_list: List[Evidence] = evidences.get("VisionInspector", [])

    if not pdf_path or not Path(pdf_path).exists():
        vision_evidence_list.append(
            Evidence(
                goal="PDF report provided for image extraction",
                found=False,
                content=None,
                location="n/a",
                rationale="No valid pdf_path supplied in AgentState.",
                confidence=0.2,
            )
        )
        return {"evidences": {"VisionInspector": vision_evidence_list}}
        
    try:
        images = extract_images_from_pdf(pdf_path)
    except Exception as e:
        vision_evidence_list.append(
            Evidence(
                goal="PDF images extracted successfully",
                found=False,
                content=str(e),
                location=pdf_path,
                rationale="PyMuPDF failed to extract images from the report.",
                confidence=0.3,
            )
        )
        return {"evidences": {"VisionInspector": vision_evidence_list}}

    if not images:
        vision_evidence_list.append(
            Evidence(
                goal="Report contains architectural diagrams",
                found=False,
                content="0 images found",
                location=pdf_path,
                rationale="The report does not contain any images or diagrams.",
                confidence=0.9,
            )
        )
        return {"evidences": {"VisionInspector": vision_evidence_list}}
        
    # Analyze the first extracted image as a heuristic
    first_img = images[0]
    llm_analysis = analyze_diagram_with_llm(
        image_b64=first_img["data"],
        mime_type=first_img["ext"]
    )
    
    is_valid_diagram = llm_analysis.get("is_stategraph", False)
    rationale = llm_analysis.get("rationale", "No rationale provided by Vision model.")
    
    vision_evidence_list.append(
        Evidence(
            goal="Diagram accurately represents the StateGraph architecture",
            found=is_valid_diagram,
            content=f"Evaluated Page {first_img['page']}, Image Index {first_img['index']}",
            location=pdf_path,
            rationale=rationale,
            confidence=0.8,
        )
    )

    return {"evidences": {"VisionInspector": vision_evidence_list}}
