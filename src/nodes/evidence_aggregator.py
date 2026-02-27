from src.state import AgentState, Evidence

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
    return {"evidences": {"EvidenceAggregator": summary_list}}