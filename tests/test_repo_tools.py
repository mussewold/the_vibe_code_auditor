import os
import subprocess
from pathlib import Path

import pytest

from src.tools.repo_tools import (
    analyze_state_structure,
    extract_git_history,
    clone_repo_sandbox,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def create_fake_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "fake_repo"
    repo_path.mkdir()

    # initialize git repository
    subprocess.run(["git", "init"], cwd=repo_path, check=True)

    src_dir = repo_path / "src"
    src_dir.mkdir()

    # typed state file (BaseModel-style)
    state_code = '''
from pydantic import BaseModel

class AgentState(BaseModel):
    value: int
'''
    (src_dir / "state.py").write_text(state_code)

    # graph file with fan-out and fan-in topology
    graph_code = '''
from langgraph.graph import StateGraph

builder = StateGraph(dict)

builder.add_edge("START", "A")
builder.add_edge("A", "B")
builder.add_edge("A", "C")
builder.add_edge("B", "END")
builder.add_edge("C", "END")
'''
    (src_dir / "graph.py").write_text(graph_code)

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial graph setup"],
        cwd=repo_path,
        check=True,
    )

    return repo_path


# ---------------------------------------------------------
# analyze_state_structure
# ---------------------------------------------------------
def test_analyze_state_structure_detects_graph_and_state(tmp_path: Path):
    repo_path = create_fake_repo(tmp_path)

    result = analyze_state_structure(str(repo_path))

    assert result["state_files_found"] is True
    assert result["typed_state_detected"] is True
    assert result["stategraph_detected"] is True

    # edges and topology
    edges = set(result["edges"])
    assert ("START", "A") in edges
    assert ("A", "B") in edges
    assert ("A", "C") in edges
    assert ("B", "END") in edges
    assert ("C", "END") in edges

    assert result["fan_out_detected"] is True
    assert result["fan_in_detected"] is True

    # no AST errors during analysis
    assert result["errors"] == []


def test_analyze_state_structure_on_empty_repo(tmp_path: Path):
    repo_path = tmp_path / "empty_repo"
    repo_path.mkdir()

    result = analyze_state_structure(str(repo_path))

    assert result["state_files_found"] is False
    assert result["typed_state_detected"] is False
    assert result["stategraph_detected"] is False
    assert result["edges"] == []
    assert result["fan_out_detected"] is False
    assert result["fan_in_detected"] is False
    assert result["errors"] == []


# ---------------------------------------------------------
# extract_git_history
# ---------------------------------------------------------
def test_extract_git_history_on_real_repo(tmp_path: Path):
    repo_path = create_fake_repo(tmp_path)

    history = extract_git_history(str(repo_path))

    assert history["errors"] is None
    assert history["commit_count"] >= 1
    assert isinstance(history["commits"], list)
    assert history["development_style"] in {
        "monolithic",
        "weakly_atomic",
        "atomic_iterative",
    }

    for commit in history["commits"]:
        assert {"hash", "timestamp", "message"} <= commit.keys()


def test_extract_git_history_non_git_directory(tmp_path: Path):
    repo_path = tmp_path / "not_a_repo"
    repo_path.mkdir()

    history = extract_git_history(str(repo_path))

    assert history["commit_count"] == 0
    assert history["commits"] == []
    assert history["errors"] is not None


# ---------------------------------------------------------
# clone_repo_sandbox
# ---------------------------------------------------------
def test_clone_repo_sandbox_success(monkeypatch, tmp_path: Path):
    invoked = {}

    def fake_run(cmd, **kwargs):
        invoked["cmd"] = cmd

        # simulate successful git clone
        class DummyCompleted:
            def __init__(self):
                self.stdout = ""
                self.stderr = ""
                self.returncode = 0

        return DummyCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)

    cloned_path = clone_repo_sandbox("https://example.com/repo.git")

    assert isinstance(cloned_path, str)
    assert os.path.isdir(cloned_path)

    # ensure git clone was requested
    assert invoked["cmd"][0] == "git"
    assert invoked["cmd"][1] == "clone"


def test_clone_repo_sandbox_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="fatal: repository not found",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc:
        clone_repo_sandbox("https://example.com/private.git")

    assert "Git clone failed" in str(exc.value)