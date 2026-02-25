import ast
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set


# ==========================================================
# AST FORENSIC ANALYZER
# ==========================================================

class GraphAnalyzer(ast.NodeVisitor):
    """
    LangGraph forensic analyzer.

    Detects:
    - Typed state schemas (Pydantic BaseModel / TypedDict)
    - StateGraph instantiation
    - Graph wiring (edges + conditional edges)
    """

    def __init__(self):
        # protocol A
        self.typed_state_detected: bool = False

        # protocol B
        self.stategraph_detected: bool = False
        self.builder_variables: Set[str] = set()
        self.edges: List[Tuple[str, str]] = []

        # import alias tracking
        self.base_model_aliases = {"BaseModel"}
        self.typeddict_aliases = {"TypedDict"}
        self.stategraph_aliases = {"StateGraph"}

    # --------------------------------------------------
    # IMPORT TRACKING (VERY IMPORTANT)
    # --------------------------------------------------
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""

        for name in node.names:
            alias = name.asname or name.name

            if module.startswith("pydantic") and name.name == "BaseModel":
                self.base_model_aliases.add(alias)

            if name.name == "TypedDict":
                self.typeddict_aliases.add(alias)

            if name.name == "StateGraph":
                self.stategraph_aliases.add(alias)

        self.generic_visit(node)

    # --------------------------------------------------
    # STATEGRAPH INSTANTIATION
    # builder = StateGraph(...)
    # --------------------------------------------------
    def visit_Assign(self, node: ast.Assign):

        if isinstance(node.value, ast.Call):

            func = node.value.func

            if isinstance(func, ast.Name):
                if func.id in self.stategraph_aliases:
                    self.stategraph_detected = True

                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.builder_variables.add(target.id)

        self.generic_visit(node)

    # --------------------------------------------------
    # TYPED STATE DETECTION
    # --------------------------------------------------
    def visit_ClassDef(self, node: ast.ClassDef):

        for base in node.bases:

            # BaseModel inheritance
            if isinstance(base, ast.Name):
                if base.id in self.base_model_aliases:
                    self.typed_state_detected = True

                if base.id in self.typeddict_aliases:
                    self.typed_state_detected = True

            # pydantic.BaseModel style
            if isinstance(base, ast.Attribute):
                if base.attr == "BaseModel":
                    self.typed_state_detected = True

        self.generic_visit(node)

    # --------------------------------------------------
    # EDGE DETECTION
    # builder.add_edge("a","b")
    # builder.add_conditional_edges(...)
    # --------------------------------------------------
    def visit_Call(self, node: ast.Call):

        if isinstance(node.func, ast.Attribute):

            attr = node.func.attr

            if attr in ("add_edge", "add_conditional_edges"):

                owner = node.func.value
                if isinstance(owner, ast.Name):
                    if owner.id in self.builder_variables:

                        args = []
                        for arg in node.args:
                            if isinstance(arg, ast.Constant):
                                args.append(arg.value)

                        if len(args) >= 2:
                            self.edges.append((args[0], args[1]))

        self.generic_visit(node)


# ==========================================================
# PROTOCOL A + B
# ==========================================================

def analyze_state_structure(path: str) -> Dict[str, Any]:

    repo_path = Path(path)

    results: Dict[str, Any] = {
        "state_files_found": False,
        "typed_state_detected": False,
        "stategraph_detected": False,
        "edges": [],
        "fan_out_detected": False,
        "fan_in_detected": False,
        "files_analyzed": [],
        "errors": [],
    }

    # --------------------------------------------------
    # locate canonical files
    # --------------------------------------------------
    state_file = repo_path / "src" / "state.py"
    graph_file = repo_path / "src" / "graph.py"

    if state_file.exists() or graph_file.exists():
        results["state_files_found"] = True

    python_files = list(repo_path.rglob("*.py"))

    # --------------------------------------------------
    # AST SCAN
    # --------------------------------------------------
    analyzer = GraphAnalyzer()
    for py_file in python_files:
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            analyzer.visit(tree)
            results["files_analyzed"].append(str(py_file))

        except Exception as e:
            results["errors"].append(f"{py_file}: {e}")

    results["typed_state_detected"] |= analyzer.typed_state_detected
    results["stategraph_detected"] |= analyzer.stategraph_detected
    results["edges"].extend(analyzer.edges)

    # --------------------------------------------------
    # TOPOLOGY ANALYSIS
    # --------------------------------------------------
    forward = {}
    reverse = {}

    for src, dst in results["edges"]:
        forward.setdefault(src, []).append(dst)
        reverse.setdefault(dst, []).append(src)

    # fan-out = one node → multiple children
    results["fan_out_detected"] = any(
        len(v) > 1 for v in forward.values()
    )

    # fan-in = multiple parents → one node
    results["fan_in_detected"] = any(
        len(v) > 1 for v in reverse.values()
    )

    return results


# ==========================================================
# PROTOCOL C — GIT FORENSICS
# ==========================================================

def extract_git_history(path: str) -> Dict[str, Any]:

    result = {
        "commit_count": 0,
        "commits": [],
        "development_style": "unknown",
        "errors": None,
    }

    try:
        cmd = [
            "git",
            "-C",
            path,
            "log",
            "--reverse",
            "--pretty=format:%h|%ad|%s",
            "--date=iso",
        ]

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
        )

        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip())

        for line in completed.stdout.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                result["commits"].append({
                    "hash": parts[0],
                    "timestamp": parts[1],
                    "message": parts[2],
                })

        result["commit_count"] = len(result["commits"])

        if result["commit_count"] <= 1:
            result["development_style"] = "monolithic"
        elif result["commit_count"] <= 3:
            result["development_style"] = "weakly_atomic"
        else:
            result["development_style"] = "atomic_iterative"

    except Exception as e:
        result["errors"] = str(e)

    return result


# ==========================================================
# SAFE SANDBOX CLONE
# ==========================================================

def clone_repo_sandbox(repo_url: str) -> str:

    temp_dir = tempfile.mkdtemp(prefix="repo_investigator_")

    try:
        subprocess.run(
            ["git", "clone", "--depth", "50", repo_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Git clone failed (auth/network error): {e.stderr}"
        )

    return temp_dir