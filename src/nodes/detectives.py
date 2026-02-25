from typing import Dict, List

from src.state import AgentState, Evidence
from src.tools.repo_tools import (
    analyze_directory_structure,
    analyze_graph_structure,
    clone_repo_sandbox,
    extract_git_history,
)


def _summarize_repo_forensics(
    directory_findings: Dict,
    graph_findings: Dict,
    history: Dict,
) -> str:
    """
    Create a human-readable forensic summary for the RepoInvestigator.
    """

    lines: List[str] = []

    # Directory / artifact overview
    lines.append("Repository Forensic Summary:")

    if directory_findings:
        lines.append("\n[Structure]")
        for path, exists in directory_findings.get("directories", {}).items():
            lines.append(f"- dir {path}: {'present' if exists else 'missing'}")
        for path, exists in directory_findings.get("files", {}).items():
            lines.append(f"- file {path}: {'present' if exists else 'missing'}")

    # Graph structure
    if graph_findings:
        lines.append("\n[LangGraph Structure]")
        if graph_findings.get("stategraph_detected"):
            lines.append("- StateGraph: detected")
        else:
            lines.append("- StateGraph: not detected")

        if graph_findings.get("typed_state_detected"):
            lines.append("- Typed state model: detected")
        else:
            lines.append("- Typed state model: not detected")

        edges = graph_findings.get("edges", []) or []
        if edges:
            lines.append("- Edges:")
            for src, dst in edges:
                lines.append(f"  - {src} -> {dst}")

        if graph_findings.get("fan_out_detected"):
            lines.append("- Fan-out: detected (branching from a single node)")
        else:
            lines.append("- Fan-out: not detected")

    # Git history
    if history:
        lines.append("\n[Git History]")
        if history.get("errors"):
            lines.append(f"- Error reading history: {history['errors']}")
        else:
            commit_count = history.get("commit_count", 0)
            lines.append(f"- Commit count: {commit_count}")
            if history.get("is_monolithic"):
                lines.append("- Pattern: monolithic or near-monolithic history")
            else:
                lines.append("- Pattern: incremental history")

            commits = history.get("commits", []) or []
            if commits:
                lines.append("- First commits:")
                for commit in commits[:5]:
                    message = commit.get("message")
                    lines.append(
                        f"  - {commit.get('hash')} "
                        f"@ {commit.get('timestamp')}: "
                        f'\"{message}\"'
                    )

    return "\n".join(lines)


def repo_investigator_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs repository forensics:

    - Clones the target repository into a sandboxed temp directory.
    - Uses AST-based analysis to detect LangGraph structures.
    - Uses git log to build a lightweight commit narrative.
    - Emits structured Evidence into the graph state.
    """

    repo_url = state.get("repo_url", "")

    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}
    repo_evidence_list: List[Evidence] = evidences.get("RepoInvestigator", [])

    if not repo_url:
        repo_evidence_list.append(
            Evidence(
                goal="Repository URL provided",
                found=False,
                content=None,
                location="n/a",
                rationale="No repo_url supplied in AgentState; "
                "cannot perform repository forensics.",
                confidence=0.2,
            )
        )
        evidences["RepoInvestigator"] = repo_evidence_list
        state["evidences"] = evidences
        return state

    try:
        local_repo_path = clone_repo_sandbox(repo_url)
    except Exception as e:  # git auth / network / repo errors
        repo_evidence_list.append(
            Evidence(
                goal="Repository successfully cloned into sandbox",
                found=False,
                content=str(e),
                location=repo_url,
                rationale="Failed to clone repository into a sandboxed "
                "directory. This is often due to authentication or "
                "network issues.",
                confidence=0.4,
            )
        )
        evidences["RepoInvestigator"] = repo_evidence_list
        state["evidences"] = evidences
        return state

    # At this point we have a local sandboxed clone; all subsequent analysis
    # operates only on that local path.
    directory_findings = analyze_directory_structure(local_repo_path)
    graph_findings = analyze_graph_structure(local_repo_path)
    history = extract_git_history(local_repo_path)

    summary = _summarize_repo_forensics(
        directory_findings=directory_findings,
        graph_findings=graph_findings,
        history=history,
    )

    repo_evidence_list.append(
        Evidence(
            goal="Repository satisfies LangGraph forensic requirements",
            found=bool(graph_findings.get("stategraph_detected"))
            and not bool(history.get("errors")),
            content=summary,
            location=local_repo_path,
            rationale=(
                "Analyzed a sandboxed clone of the repository using the "
                "Python AST module for StateGraph/typed-state detection and "
                "git log for commit history, without relying on regex."
            ),
            confidence=0.8,
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