from typing import Any, Dict, List

from src.state import (
    AgentState,
    AuditReport,
    CriterionResult,
    Evidence,
    JudicialOpinion,
)
from src.tools.chief_justice_tools import (
    dissent_summary,
    final_score_for_criterion,
    get_opinions_by_criterion,
    remediation_for_criterion,
)


def chief_justice_node(state: AgentState) -> AgentState:
    """
    Chief Justice: aggregates JudicialOpinions (Prosecutor, Defense, Tech Lead) per criterion,
    applies hardcoded deliberation rules, and produces the Audit Report (Markdown-structured).

    Deliberation protocol:
    - Rule of Security: Prosecutor-identified security vulnerability caps score at 3.
    - Rule of Evidence: Defense "Deep Metacognition" overruled if no PDF report in evidence.
    - Rule of Functionality: Tech Lead confirmation on architecture carries highest weight for Architecture criterion.

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
    if not criterion_ids:
        for dim in all_dimensions:
            cid = dim.get("id")
            if cid and cid not in criterion_ids:
                criterion_ids.append(cid)
        criterion_ids = sorted(set(criterion_ids))

    criteria_results: List[CriterionResult] = []
    for criterion_id in criterion_ids:
        ops = by_criterion.get(criterion_id, {})
        prosecutor_op = ops.get("Prosecutor")
        defense_op = ops.get("Defense")
        tech_lead_op = ops.get("TechLead")

        final_score = final_score_for_criterion(
            criterion_id, prosecutor_op, defense_op, tech_lead_op, evidences
        )
        dissent = dissent_summary(
            criterion_id, prosecutor_op, defense_op, tech_lead_op
        )
        remediation = remediation_for_criterion(
            prosecutor_op, tech_lead_op, final_score
        )

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
                remediation=remediation,
            )
        )

    overall_score = (
        sum(c.final_score for c in criteria_results) / len(criteria_results)
        if criteria_results
        else 0.0
    )
    repo_url = state.get("repo_url") or ""

    remediation_plan = "\n\n".join(
        f"## {c.dimension_name} ({c.dimension_id})\n{c.remediation}"
        for c in criteria_results
    )

    executive_summary_parts = [
        "# The Verdict",
        "",
        "| Criterion | Final Score |",
        "|-----------|-------------|",
    ]
    for c in criteria_results:
        executive_summary_parts.append(f"| {c.dimension_name} | {c.final_score} |")
    executive_summary_parts.extend([
        "",
        "# The Dissent",
        "",
    ])
    for c in criteria_results:
        executive_summary_parts.append(f"## {c.dimension_name}")
        executive_summary_parts.append("")
        executive_summary_parts.append(c.dissent_summary or "")
        executive_summary_parts.append("")
    executive_summary_parts.extend([
        "",
        "# The Remediation Plan",
        "",
        remediation_plan,
    ])

    executive_summary = "\n".join(executive_summary_parts)

    report = AuditReport(
        repo_url=repo_url,
        executive_summary=executive_summary,
        overall_score=round(overall_score, 2),
        criteria=criteria_results,
        remediation_plan=remediation_plan,
    )
    return {"final_report": report}