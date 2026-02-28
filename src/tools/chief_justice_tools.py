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


def rule_of_evidence_hallucination(
    judge_op: JudicialOpinion | None,
    evidences: Dict[str, List[Evidence]],
) -> bool:
    """
    If a Judge claims a feature exists (e.g. parallelism, reducer) 
    that the RepoInvestigator found no evidence for, overrule it.
    """
    if judge_op is None or not (judge_op.argument or "").strip():
        return False
        
    arg = (judge_op.argument or "").lower()
    repo_evs = evidences.get("RepoInvestigator", [])
    repo_content = "\n".join((ev.content or "").lower() for ev in repo_evs)
    
    # Check for parallelism hallucination
    if "parallel" in arg or "fan-out" in arg:
        if "parallel fan-out architecture: not detected" in repo_content or "no edges discovered" in repo_content:
            return True
            
    # Check for state/reducer hallucination
    if "reducer" in arg or "operator.add" in arg or "operator.ior" in arg:
        has_reducer_signal = any(
            marker in repo_content 
            for marker in ["operator.add", "operator.ior", "reducer"]
        )
        if not has_reducer_signal:
            return True
            
    return False


def final_score_for_criterion(
    criterion_id: str,
    prosecutor_op: JudicialOpinion | None,
    defense_op: JudicialOpinion | None,
    tech_lead_op: JudicialOpinion | None,
    evidences: Dict[str, List[Evidence]],
) -> int:
    """Apply deliberation rules to compute final score (1–5)."""
    
    # Rule of Evidence: Filter or penalize hallucinating opinions
    judge_ops = [prosecutor_op, defense_op, tech_lead_op]
    valid_scores = []
    
    for op in judge_ops:
        if op is None:
            continue
        if rule_of_evidence_hallucination(op, evidences):
            # Overrule: Cap score at 2 if they are hallucinating features
            valid_scores.append(min(op.score, 2))
        else:
            valid_scores.append(op.score)

    if not valid_scores:
        return 3

    # Rule of Functionality: Tech Lead weight for architecture
    if criterion_id in ARCHITECTURE_CRITERION_IDS and tech_lead_op is not None:
        # If Tech Lead is valid (not hallucinating), it carries 50% weight
        is_hallucinating = rule_of_evidence_hallucination(tech_lead_op, evidences)
        if not is_hallucinating:
            other_scores = [s for s in valid_scores if s != tech_lead_op.score]
            if other_scores:
                score = int((0.5 * tech_lead_op.score) + (0.5 * sum(other_scores)/len(other_scores)) + 0.5)
            else:
                score = tech_lead_op.score
        else:
            score = int(sum(valid_scores) / len(valid_scores) + 0.5)
    else:
        score = int(sum(valid_scores) / len(valid_scores) + 0.5)

    # Rule of Security: Cap at 3
    if rule_of_security(prosecutor_op):
        score = min(score, 3)

    return max(1, min(5, score))


def detect_score_variance(
    prosecutor_op: JudicialOpinion | None,
    defense_op: JudicialOpinion | None,
    tech_lead_op: JudicialOpinion | None,
) -> bool:
    """True if the difference between any two judge scores is > 2."""
    scores = [
        op.score 
        for op in (prosecutor_op, defense_op, tech_lead_op) 
        if op is not None
    ]
    if len(scores) < 2:
        return False
    return (max(scores) - min(scores)) > 2


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
