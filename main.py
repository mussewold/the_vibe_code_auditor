from __future__ import annotations

import argparse
from typing import Any, Dict, List

from src.graph import graph


def build_initial_state(repo_url: str) -> Dict[str, Any]:
    """
    Construct a minimal AgentState payload for the LangGraph run.
    """

    return {
        "repo_url": repo_url,
        "pdf_path": "",
        "rubric_dimensions": [],
        "evidences": {},
        "opinions": [],
        "final_report": None,
    }


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the Automaton Auditor LangGraph.",
    )
    parser.add_argument(
        "--repo-url",
        required=True,
        help="Git repository URL to audit.",
    )

    args = parser.parse_args(argv)

    state = build_initial_state(
        repo_url=args.repo_url,
    )

    result_state = graph.invoke(state)

    print("=== Automaton Auditor run complete ===")
    print(f"Repo URL: {result_state.get('repo_url')}")
    print(f"Evidence keys: {list(result_state.get('evidences', {}).keys())}")
    print(f"Opinions count: {len(result_state.get('opinions', []))}")
    print(f"Final report present: {result_state.get('final_report') is not None}")


if __name__ == "__main__":
    main()

