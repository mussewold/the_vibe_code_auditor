import os
from typing import Any, Dict, List

from src.state import AgentState, Evidence, JudicialOpinion
from src.tools.justice_tools import (
    flatten_evidence_snippets,
    ollama_chat,
    truncate,
)
def prosecutor_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs the prosecutor's role:

    - Reviews the evidence and the rubric.
    - Applies a highly adversarial, security-first lens.
    - Emits harsh JudicialOpinions for each rubric criterion.

    Philosophy:
    - "Trust No One. Assume Vibe Coding."
    - If the rubric demands parallel orchestration but evidence suggests
      a linear pipeline or missing fan-out/fan-in, this node MUST drive
      the score to 1.
    - If Judges are not clearly using structured Pydantic outputs, this
      node charges "Hallucination Liability" for the
      `structured_output_enforcement` criterion.
    """
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}
    existing_opinions_raw: List[Any] = state.get("opinions", []) or []
    existing_opinions: List[JudicialOpinion] = [
        op for op in existing_opinions_raw if isinstance(op, JudicialOpinion)
    ]

    # Collect all rubric dimensions the Prosecutor should opine on.
    github_rubric: List[Dict] = state.get("github_rubric") or []
    pdf_report_rubric: List[Dict] = state.get("pdf_report_rubric") or []
    pdf_images_rubric: List[Dict] = state.get("pdf_images_rubric") or []

    all_dimensions: List[Dict] = (
        github_rubric + pdf_report_rubric + pdf_images_rubric
    )

    prosecutor_opinions: List[JudicialOpinion] = []

    for dim in all_dimensions:
        criterion_id = dim.get("id")
        if not criterion_id:
            continue
        criterion_name = str(dim.get("name") or "")
        forensic_instruction = str(dim.get("forensic_instruction") or "")

        score = 2  # default skeptical baseline
        missing_elements: List[str] = []
        argument_chunks: List[str] = [
            'Core philosophy: "Trust No One. Assume Vibe Coding."',
        ]
        charges: List[str] = []

        # --------------------------------------------------
        # Special case: Graph Orchestration / Parallelism
        # --------------------------------------------------
        is_parallelism_criterion = (
            criterion_id == "graph_orchestration"
            or "fan-out" in forensic_instruction.lower()
            or "fan-in" in forensic_instruction.lower()
            or "parallel" in criterion_name.lower()
        )

        if is_parallelism_criterion:
            repo_evs = evidences.get("RepoInvestigator", [])
            repo_summary_text = "\n".join(
                ev.content or "" for ev in repo_evs
            )

            # Look for explicit signals that parallel fan‑out/fan‑in
            # was NOT detected in the codebase.
            fan_out_missing = any(
                marker in repo_summary_text
                for marker in [
                    "Parallel fan-out architecture: NOT detected",
                    "No edges discovered",
                ]
            )

            if fan_out_missing:
                # Rubric demands parallel orchestration but the
                # forensic evidence points to a linear or under-specified
                # pipeline → automatic score of 1.
                score = 1
                missing_elements.append(
                    "Explicit parallel fan-out/fan-in pattern for both Detectives "
                    "and Judges in the StateGraph wiring."
                )
                charges.append("Bypassed Structure (claimed parallel, built linear)")

            # Cross-check with any vision evidence about diagrams.
            vision_evs = evidences.get("VisionInspector", [])
            if any(not ev.found for ev in vision_evs):
                score = 1
                missing_elements.append(
                    "Accurate StateGraph diagram that clearly distinguishes "
                    "parallel branches from sequential steps."
                )
                charges.append("Misleading Architecture Visual / Missing Diagram Proof")

            argument_chunks.append(
                "If the rubric asks for Parallel Orchestration but the evidence "
                "shows a linear pipeline (or missing fan-out/fan-in markers), "
                "I argue for a score of 1. I look specifically for bypassed "
                "structure (no parallel branches, no synchronization node, "
                "no conditional edges)."
            )

        # --------------------------------------------------
        # Special case: Structured Output Enforcement
        # --------------------------------------------------
        elif criterion_id == "structured_output_enforcement":
            invalid_types = [
                type(op).__name__
                for op in existing_opinions_raw
                if not isinstance(op, JudicialOpinion)
            ]
            has_structured = bool(existing_opinions)

            if not has_structured:
                # No validated JudicialOpinion objects means the Judges are
                # effectively free‑text or missing; this is a direct violation
                # of the rubric's structured-output requirement.
                score = 1
                missing_elements.extend(
                    [
                        "Judge nodes that bind the model to the JudicialOpinion "
                        "schema (structured output enforcement).",
                        "Validation and retry logic when LLM outputs malformed "
                        "or free‑form text instead of JSON.",
                    ]
                )
                charges.append("Hallucination Liability (unstructured judge outputs)")
                argument_chunks.append(
                    "No structured JudicialOpinion instances are present in state. "
                    "Under 'Hallucination Liability', I assume Judges are returning "
                    "freeform text or are not wired with schema enforcement at all. "
                    "This warrants the lowest possible score."
                )
            elif invalid_types:
                score = 1
                missing_elements.append(
                    "Judges must return validated Pydantic JudicialOpinion models; "
                    f"observed non-model opinion payload types: {sorted(set(invalid_types))}."
                )
                charges.append("Hallucination Liability (mixed/freeform opinion payloads)")
                argument_chunks.append(
                    "Judges are producing outputs that are not validated Pydantic "
                    "models. That is exactly the kind of vibe-coded parsing that "
                    "creates silent grading hallucinations. Score must be 1."
                )
            else:
                # Even when structured objects exist, the Prosecutor does not
                # reward unproven implementation details with a perfect score.
                score = 2
                argument_chunks.append(
                    "Structured JudicialOpinion objects exist, but there is no "
                    "runtime proof that Judge nodes actually enforce schema via "
                    "structured-output bindings with retry logic. I assign a "
                    "conservative, non-passing score."
                )

        # --------------------------------------------------
        # Generic skeptical handling for all other criteria
        # --------------------------------------------------
        else:
            # For criteria without explicit programmatic checks, the
            # Prosecutor defaults to a conservative score and documents
            # that unproven claims are not granted full credit.
            score = 2
            argument_chunks.append(
                "Applying the 'Trust No One' rule, I treat unverified rubric "
                "claims as only partially satisfied. Without hard evidence tied "
                "to this criterion, I withhold higher scores."
            )

        if charges:
            argument_chunks.append("Charges:\n- " + "\n- ".join(charges))

        if missing_elements:
            argument_chunks.append(
                "Specific missing elements I am charging:\n- "
                + "\n- ".join(missing_elements)
            )

        # Cite all evidence locations consulted so the Chief Justice can
        # cross-check this opinion against concrete artifacts.
        cited_evidence = [
            ev.location
            for ev_list in evidences.values()
            for ev in ev_list
        ]

        # --------------------------------------------------
        # Optional: use Ollama (local) to draft the argument prose
        # --------------------------------------------------
        ollama_model = os.environ.get("OLLAMA_MODEL")
        ollama_host = os.environ.get("OLLAMA_HOST")
        use_ollama = (
            os.environ.get("USE_OLLAMA", "1").strip()
            not in {"0", "false", "False"}
        )

        argument_text = " ".join(argument_chunks).strip()

        if use_ollama and ollama_model and ollama_host:
            evidence_snippets = flatten_evidence_snippets(evidences)
            prompt = """
                You are the Prosecutor, an adversarial forensic auditor. Your core philosophy is: 'Trust No One. Assume Vibe Coding.'
                Your goal is to scrutinize evidence for gaps, security flaws, and orchestration fraud. For the provided criterion, you must:
                - Identify Failure Patterns: Look specifically for linear execution when parallelism is required or missing state reducers.
                - Cite Hard Evidence: Do not just list filenames. You must extract and cite specific commit hashes, code line numbers, or JSON keys that prove the implementation is lacking.
                - Charge the Defendant: If the evidence is missing or weak, explicitly charge them with 'Orchestration Fraud' or 'Hallucination Liability' and cap their score accordingly.
                - Output Format: You must return a valid JudicialOpinion JSON object.
            """.strip()

            drafted = ollama_chat(
                model=ollama_model,
                prompt=truncate(prompt, 12000),
                host=ollama_host,
                timeout_s=40.0,
            )
            if drafted:
                argument_text = drafted

        prosecutor_opinions.append(
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id=criterion_id,
                score=score,
                argument=argument_text,
                cited_evidence=cited_evidence,
            )
        )

    # AgentState uses an additive reducer for `opinions`, so returning
    # a dict with a list here will append these to any existing opinions.
    return {"opinions": prosecutor_opinions}


def defense_attorney_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs the defense attorney's role (The Optimistic Lens):

    - Reviews the evidence and rubric through "Reward Effort and Intent."
    - Looks for the "Spirit of the Law": creative workarounds, deep thought, iteration.
    - Uses local Ollama to draft generous arguments; emits JudicialOpinions per criterion.
    """
    evidences: Dict[str, List[Evidence]] = state.get("evidences", {}) or {}

    github_rubric: List[Dict] = state.get("github_rubric") or []
    pdf_report_rubric: List[Dict] = state.get("pdf_report_rubric") or []
    pdf_images_rubric: List[Dict] = state.get("pdf_images_rubric") or []

    all_dimensions: List[Dict] = (
        github_rubric + pdf_report_rubric + pdf_images_rubric
    )

    defense_opinions: List[JudicialOpinion] = []

    # Precompute signals from evidence for "Engineering Process" / "Master Thinker"
    repo_evs = evidences.get("RepoInvestigator", [])
    repo_text = "\n".join(ev.content or "" for ev in repo_evs).lower()
    doc_evs = evidences.get("DocAnalyst", [])
    doc_text = "\n".join(ev.content or "" for ev in doc_evs).lower()

    has_git_story = any(
        phrase in repo_text
        for phrase in [
            "commit",
            "history",
            "iteration",
            "branch",
            "merge",
            "reducer",
            "state",
        ]
    )
    has_architecture_depth = any(
        phrase in doc_text
        for phrase in [
            "langgraph",
            "state reducer",
            "reducer",
            "stategraph",
            "fan-out",
            "fan-in",
            "orchestration",
        ]
    )

    ollama_model = os.environ.get("OLLAMA_MODEL")
    ollama_host = os.environ.get("OLLAMA_HOST")
    use_ollama = (
        os.environ.get("USE_OLLAMA", "1").strip()
        not in {"0", "false", "False"}
    )
    evidence_snippets = flatten_evidence_snippets(evidences) if use_ollama else ""

    for dim in all_dimensions:
        criterion_id = dim.get("id")
        if not criterion_id:
            continue
        criterion_name = str(dim.get("name") or "")
        forensic_instruction = str(dim.get("forensic_instruction") or "")

        # Generous baseline: 4. Bump to 5 when effort/architecture signals are strong.
        score = 4
        strengths: List[str] = []

        if has_git_story:
            strengths.append(
                "Git/repo evidence suggests a story of iteration and engineering process."
            )
        if has_architecture_depth:
            strengths.append(
                "Architecture or report evidence shows engagement with LangGraph concepts (e.g. state reducers, orchestration)."
            )

        if has_git_story and has_architecture_depth:
            score = 5
            strengths.append(
                "Combined evidence supports a 'Master Thinker' profile: deep understanding even if implementation has rough edges."
            )

        argument_chunks: List[str] = [
            'Core philosophy: "Reward Effort and Intent. Look for the Spirit of the Law."',
            "I highlight creative workarounds, deep thought, and effort even when implementation is imperfect.",
        ]
        if strengths:
            argument_chunks.append("Strengths observed:\n- " + "\n- ".join(strengths))

        # Unique cited evidence
        cited_evidence: List[str] = []
        seen_locations: set = set()
        for ev_list in evidences.values():
            for ev in ev_list:
                loc = (ev.location or "").strip()
                if loc and loc not in seen_locations:
                    seen_locations.add(loc)
                    cited_evidence.append(loc)

        argument_text = " ".join(argument_chunks).strip()

        if use_ollama and ollama_model and ollama_host and evidence_snippets:
            prompt = f"""
        You are the Defense Attorney in a software code courtroom (The Optimistic Lens).
        Your core philosophy is: "Reward Effort and Intent. Look for the Spirit of the Law."

        You are producing the argument field of a JudicialOpinion that highlights strengths and argues for a generous score.

        Context for this opinion:
        - judge: "Defense"
        - criterion_id: {criterion_id}
        - criterion_name: {criterion_name}
        - forensic_instruction: {forensic_instruction}
        - score (already set): {score}

        Structured reasoning so far:
        {argument_text}

        Evidence from the Detective layer (summarised):
        {evidence_snippets}

        Your task:
        1. If the code or repo is imperfect but the architecture report or docs show deep understanding of LangGraph, state reducers, or orchestration, argue that the student matches the "Master Thinker" profile despite syntax or implementation gaps.
        2. If Git history or repo evidence suggests struggle and iteration (commits, branches, refactors), argue for a higher score based on "Engineering Process" and reward the journey.
        3. Write a single, constructive paragraph that emphasizes strengths, intent, and the spirit of the law. Output ONLY the argument prose—no JSON, no labels, no meta-commentary.
        """.strip()

            drafted = ollama_chat(
                model=ollama_model,
                prompt=truncate(prompt, 12000),
                host=ollama_host,
                timeout_s=40.0,
            )
            if drafted:
                argument_text = drafted

        defense_opinions.append(
            JudicialOpinion(
                judge="Defense",
                criterion_id=criterion_id,
                score=score,
                argument=argument_text,
                cited_evidence=cited_evidence,
            )
        )

    return {"opinions": defense_opinions}


def tech_lead_node(state: AgentState) -> AgentState:
    """
    LangGraph node that performs the tech lead's role:  

    - Reviews the evidence and the opinions.
    - Provides a final report.
    """
    return {}