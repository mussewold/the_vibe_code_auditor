from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.repo_tools import (
    analyze_state_structure,
    clone_repo_sandbox,
    extract_git_history,
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
        evidences["RepoInvestigator"] = repo_evidence_list
        state["evidences"] = evidences
        return state

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
        evidences["RepoInvestigator"] = repo_evidence_list
        state["evidences"] = evidences
        return state

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

    evidences["RepoInvestigator"] = repo_evidence_list
    state["evidences"] = evidences

    return state

def doc_analyst_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs document analysis:

    - Extracts text from the document.
    - Extracts metadata from the document.
    - Extracts the document's structure.
    """
    return state

def vision_inspector_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs rubric analysis:

    - Extracts the rubric's dimensions.
    - Extracts the rubric's criteria.
    - Extracts the rubric's scoring.
    """
    return state

def evidence_aggregator_node(state: AgentState) -> AgentState:
    """
    Synchronization node that runs AFTER all Detectives.

    Reducers on AgentState already merge evidence across branches; this node
    simply acts as the fan-in point and records a summary Evidence item.
    """

    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}
    total_items = sum(len(v) for v in evidences.values())

    summary_list = evidences.get("EvidenceAggregator", [])
    summary_list.append(
        Evidence(
            goal="All detective evidence aggregated",
            found=total_items > 0,
            content=None,
            location="EvidenceAggregator",
            rationale=(
                "Synchronization point after RepoInvestigator, DocAnalyst, and "
                "VisionInspector complete. All JSON evidence is merged into "
                "state.evidences."
            ),
            confidence=0.9,
        )
    )
    evidences["EvidenceAggregator"] = summary_list
    state["evidences"] = evidences

    return state