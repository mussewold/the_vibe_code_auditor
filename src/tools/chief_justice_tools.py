"""Helper functions and constants for the Chief Justice deliberation protocol."""

from typing import Dict, List

from src.state import Evidence, JudicialOpinion


# --- Deliberation protocol: hardcoded rules ---

SECURITY_MARKERS = (
    "os.system",
    "unsanitized",
    "injection",
    "security vulnerability",
    "security flaw",
    "command injection",
    "subprocess",
)

DEEP_METACOGNITION_MARKERS = (
    "deep metacognition",
    "master thinker",
    "deep understanding",
    "spirit of the law",
    "engineering process",
)

ARCHITECTURE_CRITERION_IDS = (
    "graph_orchestration",
    "state_management_rigor",
    "architecture",
)


def get_opinions_by_criterion(
    opinions: List[JudicialOpinion],
) -> Dict[str, Dict[str, JudicialOpinion]]:
    """Group opinions by criterion_id and judge."""
    by_criterion: Dict[str, Dict[str, JudicialOpinion]] = {}
    for op in opinions:
        if not isinstance(op, JudicialOpinion):
            continue
        cid = op.criterion_id
        if cid not in by_criterion:
            by_criterion[cid] = {}
        by_criterion[cid][op.judge] = op
    return by_criterion


def rule_of_security(prosecutor_op: JudicialOpinion | None) -> bool:
    """If Prosecutor identifies a confirmed security vulnerability, return True (cap score at 3)."""
    if prosecutor_op is None:
        return False
    arg = (prosecutor_op.argument or "").lower()
    return any(m in arg for m in SECURITY_MARKERS)


def rule_of_evidence_defense_overruled(
    defense_op: JudicialOpinion | None,
    evidences: Dict[str, List[Evidence]],
) -> bool:
    """If Defense claims 'Deep Metacognition' but RepoInvestigator found no PDF report, overrule Defense."""
    if defense_op is None:
        return False
    arg = (defense_op.argument or "").lower()
    if not any(m in arg for m in DEEP_METACOGNITION_MARKERS):
        return False
    doc_evs = evidences.get("DocAnalyst", [])
    repo_evs = evidences.get("RepoInvestigator", [])
    combined = doc_evs + repo_evs
    has_pdf_report = any(
        ev.found
        and (
            "pdf" in (ev.location or "").lower()
            or "report" in (ev.goal or "").lower()
        )
        for ev in combined
    )
    return not has_pdf_report


def rule_of_functionality_architecture(
    criterion_id: str,
    tech_lead_op: JudicialOpinion | None,
) -> bool:
    """If Tech Lead confirms architecture is modular and workable, return True (highest weight)."""
    if criterion_id not in ARCHITECTURE_CRITERION_IDS or tech_lead_op is None:
        return False
    arg = (tech_lead_op.argument or "").lower()
    return (
        tech_lead_op.score >= 4
        or "modular" in arg
        or "workable" in arg
        or "sound" in arg
        or "reducer" in arg
    )


def final_score_for_criterion(
    criterion_id: str,
    prosecutor_op: JudicialOpinion | None,
    defense_op: JudicialOpinion | None,
    tech_lead_op: JudicialOpinion | None,
    evidences: Dict[str, List[Evidence]],
) -> int:
    """Apply deliberation rules to compute final score (1–5)."""
    if tech_lead_op is not None:
        score = tech_lead_op.score
    elif defense_op is not None and prosecutor_op is not None:
        score = (prosecutor_op.score + defense_op.score) // 2
    elif defense_op is not None:
        score = defense_op.score
    elif prosecutor_op is not None:
        score = prosecutor_op.score
    else:
        score = 3

    if rule_of_security(prosecutor_op):
        score = min(score, 3)

    if rule_of_evidence_defense_overruled(defense_op, evidences):
        score = min(score, 3)

    if rule_of_functionality_architecture(criterion_id, tech_lead_op):
        score = max(score, tech_lead_op.score if tech_lead_op else score)

    return max(1, min(5, score))


def dissent_summary(
    criterion_id: str,
    prosecutor_op: JudicialOpinion | None,
    defense_op: JudicialOpinion | None,
    tech_lead_op: JudicialOpinion | None,
) -> str:
    """One paragraph summarizing the conflict between judges."""
    parts: List[str] = []
    if prosecutor_op is not None:
        parts.append(
            f"The Prosecutor scored {prosecutor_op.score} and argued: "
            f"{(prosecutor_op.argument or '').strip()[:200]}..."
        )
    if defense_op is not None:
        parts.append(
            f"The Defense scored {defense_op.score} and argued: "
            f"{(defense_op.argument or '').strip()[:200]}..."
        )
    if tech_lead_op is not None:
        parts.append(
            f"The Tech Lead scored {tech_lead_op.score} and argued: "
            f"{(tech_lead_op.argument or '').strip()[:200]}..."
        )
    if not parts:
        return "No judge opinions were available for this criterion."
    return " ".join(parts)


def remediation_for_criterion(
    prosecutor_op: JudicialOpinion | None,
    tech_lead_op: JudicialOpinion | None,
    final_score: int,
) -> str:
    """File-level remediation: prefer Tech Lead advice; add Prosecutor missing elements if score low."""
    instructions: List[str] = []
    if tech_lead_op and (tech_lead_op.argument or "").strip():
        instructions.append((tech_lead_op.argument or "").strip())
    if final_score <= 2 and prosecutor_op and (prosecutor_op.argument or "").strip():
        instructions.append(
            "Address gaps noted by the Prosecutor: "
            + (prosecutor_op.argument or "").strip()[:500]
        )
    if not instructions:
        return (
            "Review judge opinions and evidence; apply fixes to code or "
            "documentation as indicated."
        )
    return " ".join(instructions)[:2000]
