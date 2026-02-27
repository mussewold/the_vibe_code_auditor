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
        return {}

    data: Dict = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))

    dimensions: List[Dict] = data.get("dimensions", [])
    synthesis_rules: Dict = data.get("synthesis_rules", {})

    return {
        "rubric_dimensions": dimensions,
        "synthesis_rules": synthesis_rules,
        "github_rubric": [
            d for d in dimensions if d.get("target_artifact") == "github_repo"
        ],
        "pdf_report_rubric": [
            d for d in dimensions if d.get("target_artifact") == "pdf_report"
        ],
        "pdf_images_rubric": [
            d for d in dimensions if d.get("target_artifact") == "pdf_images"
        ]
    }

