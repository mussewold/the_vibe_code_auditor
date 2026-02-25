# tests/test_repo_tools.py

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from src.tools.repo_tools import (
    clone_repo_sandbox,
    extract_git_history,
    analyze_directory_structure,
    analyze_graph_structure,
)


# ---------------------------------------------------------
# Helper: create a minimal fake LangGraph repo
# ---------------------------------------------------------
def create_fake_repo():
    temp_dir = tempfile.mkdtemp(prefix="fake_repo_")
    repo_path = Path(temp_dir)

    subprocess.run(["git", "init"], cwd=repo_path, check=True)

    # create fake graph file
    graph_code = """
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

class AgentState(TypedDict):
    value: int

builder = StateGraph(AgentState)
builder.add_edge("START", "RepoInvestigator")
builder.add_edge("START", "DocAnalyst")
"""

    (repo_path / "graph.py").write_text(graph_code)

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial graph setup"],
        cwd=repo_path,
        check=True,
    )

    return repo_path


# ---------------------------------------------------------
# TEST: analyze_graph_structure
# ---------------------------------------------------------
def test_analyze_graph_structure_detects_graph():
    repo_path = create_fake_repo()

    result = analyze_graph_structure(str(repo_path))

    assert result["stategraph_detected"] is True
    assert result["typed_state_detected"] is True
    assert len(result["edges"]) >= 1
    assert result["fan_out_detected"] is True


# ---------------------------------------------------------
# TEST: git history extraction
# ---------------------------------------------------------
def test_extract_git_history():
    repo_path = create_fake_repo()

    history = extract_git_history(str(repo_path))

    assert history["commit_count"] >= 1
    assert isinstance(history["commits"], list)
    assert history["errors"] is None


# ---------------------------------------------------------
# TEST: sandbox clone (real world test)
# ---------------------------------------------------------
def test_clone_repo_sandbox():
    # small public repo for fast cloning
    repo_url = "https://github.com/octocat/Hello-World.git"

    cloned_path = clone_repo_sandbox(repo_url)

    assert os.path.exists(cloned_path)
    assert (Path(cloned_path) / ".git").exists()