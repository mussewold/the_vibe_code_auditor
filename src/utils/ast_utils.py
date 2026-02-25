import ast
from typing import List, Tuple


class GraphAnalyzer(ast.NodeVisitor):
    """
    AST visitor used by RepoInvestigator to verify
    LangGraph structure WITHOUT regex.

    Detects:
    - StateGraph instantiation
    - Typed state models (BaseModel / TypedDict)
    - Graph wiring via builder.add_edge()
    """

    def __init__(self):
        self.stategraph_found: bool = False
        self.typed_state_found: bool = False
        self.edges: List[Tuple[str, str]] = []

    # -------------------------------------------------
    # Detect StateGraph(...)
    # -------------------------------------------------
    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == "StateGraph":
                self.stategraph_found = True

        self.generic_visit(node)

    # -------------------------------------------------
    # Detect Typed State Definitions
    # class X(BaseModel) or class X(TypedDict)
    # -------------------------------------------------
    def visit_ClassDef(self, node: ast.ClassDef):
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ("BaseModel", "TypedDict"):
                    self.typed_state_found = True

        self.generic_visit(node)

    # -------------------------------------------------
    # Detect builder.add_edge("A", "B")
    # -------------------------------------------------
    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value

            if isinstance(call.func, ast.Attribute):
                if call.func.attr == "add_edge":

                    args = []
                    for arg in call.args:
                        if isinstance(arg, ast.Constant):
                            args.append(arg.value)

                    if len(args) == 2:
                        self.edges.append((args[0], args[1]))

        self.generic_visit(node)