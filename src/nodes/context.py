import json
from pathlib import Path
from typing import Dict, List

from src.state import AgentState


RUBRIC_PATH = Path("rubric/automaton_auditor_rubric.json")


def context_builder_node(state: AgentState) -> AgentState:
    """
    Load the central rubric JSON and distribute targeted
    dimensions into the shared AgentState.
    """

    if not RUBRIC_PATH.exists():
        # Fail gracefully; downstream nodes can still run.
        return state

    data: Dict = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))

    dimensions: List[Dict] = data.get("dimensions", [])
    synthesis_rules: Dict = data.get("synthesis_rules", {})

    state["rubric_dimensions"] = dimensions
    state["synthesis_rules"] = synthesis_rules

    # Targeting protocol: pre-slice by artifact so each
    # detective/judge can focus on relevant instructions.
    state["github_rubric"] = [
        d for d in dimensions if d.get("target_artifact") == "github_repo"
    ]
    state["pdf_report_rubric"] = [
        d for d in dimensions if d.get("target_artifact") == "pdf_report"
    ]
    state["pdf_images_rubric"] = [
        d for d in dimensions if d.get("target_artifact") == "pdf_images"
    ]

    return state

