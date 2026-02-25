from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes.context import context_builder_node
from src.nodes.detectives import (
    repo_investigator_node,
    doc_analyst_node,
    vision_inspector_node,
    evidence_aggregator_node
)
from src.nodes.justice import prosecutor_node, defense_attorney_node, tech_lead_node
from src.nodes.judges import chief_justice_node

builder = StateGraph(AgentState)

# --- Context builder ---
builder.add_node("ContextBuilder", context_builder_node)

# --- Detectives ---
builder.add_node("RepoInvestigator", repo_investigator_node)
builder.add_node("DocAnalyst", doc_analyst_node)
builder.add_node("VisionInspector", vision_inspector_node)

# Fan-out (PARALLEL)
#builder.add_edge("ContextBuilder", "RepoInvestigator")
#builder.add_edge("ContextBuilder", "DocAnalyst")
#builder.add_edge("ContextBuilder", "VisionInspector")

# --- Synchronization node ---
builder.add_node("EvidenceAggregator", evidence_aggregator_node)

# --- Judges ---
builder.add_node("Prosecutor", prosecutor_node)
builder.add_node("DefenseAttorney", defense_attorney_node)
builder.add_node("TechLead", tech_lead_node)

# --- Edges / flow ---
builder.add_edge(START, "ContextBuilder")

# Fan-out: ContextBuilder -> three Detectives
builder.add_edge("ContextBuilder", "RepoInvestigator")
builder.add_edge("ContextBuilder", "DocAnalyst")
builder.add_edge("ContextBuilder", "VisionInspector")

# Fan-in: all Detectives -> EvidenceAggregator
builder.add_edge("RepoInvestigator", "EvidenceAggregator")
builder.add_edge("DocAnalyst", "EvidenceAggregator")
builder.add_edge("VisionInspector", "EvidenceAggregator")

# --- Chief Justice ---
builder.add_node("ChiefJustice", chief_justice_node)

# --- Edges ---
builder.add_edge("EvidenceAggregator", "Prosecutor")
builder.add_edge("EvidenceAggregator", "DefenseAttorney")
builder.add_edge("EvidenceAggregator", "TechLead")
builder.add_edge("Prosecutor", "ChiefJustice")
builder.add_edge("DefenseAttorney", "ChiefJustice")
builder.add_edge("TechLead", "ChiefJustice")
builder.add_edge("ChiefJustice", END)

graph = builder.compile()
