from pathlib import Path

from src.nodes.detectives import doc_analyst_node
from src.state import AgentState, Evidence


def _make_state(tmp_path: Path, report_text: str) -> AgentState:
    report_path = tmp_path / "report.md"
    report_path.write_text(report_text, encoding="utf-8")

    # Minimal viable AgentState for this node: many fields are unused here.
    return {
        "repo_url": "",
        "pdf_path": str(report_path),
        "rubric_dimensions": [],
        "synthesis_rules": {},
        "github_rubric": [],
        "pdf_report_rubric": [],
        "pdf_images_rubric": [],
        "evidences": {},
        "opinions": [],
        "final_report": None,  # type: ignore[arg-type]
    }


def test_doc_analyst_basic_markdown(tmp_path: Path) -> None:
    report = """
We implemented parallel Judges in src/nodes/judges.py.

Our approach to Dialectical Synthesis is operational: we implement a fan-out
graph where multiple judges reason in parallel, and a fan-in node aggregates
their metacognitive reflections.
"""

    state = _make_state(tmp_path, report)
    new_state = doc_analyst_node(state)

    evidences = new_state.get("evidences", {})
    doc_evidence = evidences.get("DocAnalyst", [])

    # Sanity: some Evidence objects were produced.
    assert isinstance(doc_evidence, list)
    assert any(
        isinstance(ev, Evidence)
        and "Protocol A" in ev.goal
        for ev in doc_evidence
    )
    assert any(
        isinstance(ev, Evidence)
        and "Dialectical Synthesis" in ev.goal
        for ev in doc_evidence
    )

