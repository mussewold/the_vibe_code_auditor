import os
from typing import Any, Dict, List

from src.state import (
    AgentState,
    AuditReport,
    CriterionResult,
    Evidence,
    JudicialOpinion,
)
from src.tools.chief_justice_tools import (
    detect_score_variance,
    final_score_for_criterion,
    get_opinions_by_criterion,
)
from src.tools.justice_tools import (
    ollama_chat,
    truncate,
)


def chief_justice_node(state: AgentState) -> AgentState:
    """
    Chief Justice: aggregates JudicialOpinions (Prosecutor, Defense, Tech Lead) per criterion,
    applies deterministic deliberation rules, and synthesizes an LLM Audit Report.

    Output: AuditReport with verdict (final score per criterion), dissent summary, and remediation plan.
    """
    opinions_raw: List[Any] = state.get("opinions", []) or []
    opinions: List[JudicialOpinion] = [
        op for op in opinions_raw if isinstance(op, JudicialOpinion)
    ]
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}

    github_rubric = state.get("github_rubric") or []
    pdf_report_rubric = state.get("pdf_report_rubric") or []
    pdf_images_rubric = state.get("pdf_images_rubric") or []
    all_dimensions: List[Dict] = github_rubric + pdf_report_rubric + pdf_images_rubric
    id_to_name: Dict[str, str] = {
        str(d.get("id", "")): str(d.get("name", ""))
        for d in all_dimensions
        if d.get("id")
    }

    by_criterion = get_opinions_by_criterion(opinions)
    criterion_ids = sorted(by_criterion.keys())
    
    # Configuration
    ollama_model = os.environ.get("OLLAMA_MODEL")
    ollama_host = os.environ.get("OLLAMA_HOST")
    use_ollama = (
        os.environ.get("USE_OLLAMA", "1").strip()
        not in {"0", "false", "False"}
    )

    criteria_results: List[CriterionResult] = []
    
    for criterion_id in criterion_ids:
        ops = by_criterion.get(criterion_id, {})
        prosecutor_op = ops.get("Prosecutor")
        defense_op = ops.get("Defense")
        tech_lead_op = ops.get("TechLead")

        # 1. Deterministic Final Score
        final_score = final_score_for_criterion(
            criterion_id, prosecutor_op, defense_op, tech_lead_op, evidences
        )

        # 2. Dissent Summary (High Variance > 2)
        dissent = None
        if detect_score_variance(prosecutor_op, defense_op, tech_lead_op):
            if use_ollama and ollama_model and ollama_host:
                prompt = f"""
                You are the Chief Justice. There is high variance (>2) in judge scores for '{id_to_name.get(criterion_id)}'.
                Prosecutor ({prosecutor_op.score if prosecutor_op else 'N/A'}): {prosecutor_op.argument if prosecutor_op else ''}
                Defense ({defense_op.score if defense_op else 'N/A'}): {defense_op.argument if defense_op else ''}
                Tech Lead ({tech_lead_op.score if tech_lead_op else 'N/A'}): {tech_lead_op.argument if tech_lead_op else ''}
                
                Provide a single paragraph 'Dissent Summary' explaining the specific trade-offs (e.g., security vs innovation).
                Respond with ONLY the dissent text.
                """.strip()
                dissent = ollama_chat(model=ollama_model, prompt=truncate(prompt, 8000), host=ollama_host)
            
            if not dissent:
                dissent = f"High variance detected: Scores range from {min(s for s in [prosecutor_op.score if prosecutor_op else None, defense_op.score if defense_op else None, tech_lead_op.score if tech_lead_op else None] if s is not None)} to {max(s for s in [prosecutor_op.score if prosecutor_op else None, defense_op.score if defense_op else None, tech_lead_op.score if tech_lead_op else None] if s is not None)}. Significant conflict between judge perspectives."

        judge_opinions_for_criterion = [
            op for op in opinions if op.criterion_id == criterion_id
        ]
        
        criteria_results.append(
            CriterionResult(
                dimension_id=criterion_id,
                dimension_name=id_to_name.get(criterion_id, criterion_id),
                final_score=final_score,
                judge_opinions=judge_opinions_for_criterion,
                dissent_summary=dissent,
                remediation="Detailed in Remediation Plan",
            )
        )

    overall_score = (
        sum(c.final_score for c in criteria_results) / len(criteria_results)
        if criteria_results
        else 0.0
    )
    repo_url = state.get("repo_url") or ""

    # --- Synthesis of Audit Report Narrative ---

    # A. Executive Summary
    exec_sum_header = f"# The Verdict\n\nOverall Aggregate Score: {round(overall_score, 2)}\n\n"
    table = "| Criterion | Final Score |\n|-----------|-------------|\n"
    for c in criteria_results:
        table += f"| {c.dimension_name} | {c.final_score} |\n"
    
    executive_summary = exec_sum_header + table
    
    if use_ollama and ollama_model and ollama_host:
        prompt = f"""
        You are the Chief Justice. Synthesize a professional Executive Summary narrative for this Audit Report.
        Repo: {repo_url}
        Aggregate Score: {overall_score}
        Score Table Data: {[(c.dimension_name, c.final_score) for c in criteria_results]}
        
        Provide a concise overall verdict regarding architectural soundess and engineering rigor.
        Output ONLY the Markdown narrative.
        """.strip()
        narrative = ollama_chat(model=ollama_model, prompt=truncate(prompt, 8000), host=ollama_host)
        if narrative:
            executive_summary += "\n" + narrative

    # B. Criterion Breakdown Narrative
    breakdown_parts = ["\n# Criterion Breakdown"]
    for c in criteria_results:
        breakdown_parts.append(f"\n## {c.dimension_name} (Score: {c.final_score})")
        for op in c.judge_opinions:
            breakdown_parts.append(f"- **{op.judge}** ({op.score}): {op.argument}")
        if c.dissent_summary:
            breakdown_parts.append(f"\n> [!IMPORTANT]\n> **Dissent:** {c.dissent_summary}")

    # C. Remediation Plan
    remediation_plan = "# The Remediation Plan\n\n"
    if use_ollama and ollama_model and ollama_host:
        prompt = f"""
        You are the Chief Justice. Create a cohesive, file-level Remediation Plan.
        Focus on low scores: {[c.dimension_name for c in criteria_results if c.final_score <= 3]}
        Consult judge feedback: {[op.argument[:300] for op in opinions if op.score <= 3]}
        
        Output a structured Markdown plan with specific actionable instructions for improvement.
        """.strip()
        rem_text = ollama_chat(model=ollama_model, prompt=truncate(prompt, 8000), host=ollama_host)
        if rem_text:
            remediation_plan += rem_text
    else:
        remediation_plan += "Address gaps identified in judge opinions, particularly regarding graph orchestration and state management."

    full_narrative = (
        executive_summary + "\n" + "\n".join(breakdown_parts) + "\n\n" + remediation_plan
    )

    # D. Save to file
    os.makedirs("audit", exist_ok=True)
    with open("audit/audit_report.md", "w") as f:
        f.write(full_narrative)

    report = AuditReport(
        repo_url=repo_url,
        executive_summary=full_narrative,
        overall_score=round(overall_score, 2),
        criteria=criteria_results,
        remediation_plan=remediation_plan,
    )
    return {
        "final_report": report,
        "rendered_report": full_narrative,
    }