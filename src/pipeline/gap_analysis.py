"""
Step 3: Gap Analysis — Compare JD requirements vs resume evidence.
"""

import json
import logging
from typing import Optional

from src import config
from src.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert placement advisor performing a gap analysis.
Compare what a job description requires against what a student's resume demonstrates.

{config.GROUNDING_INSTRUCTION}

You MUST respond with valid JSON matching this exact schema:
{{
  "gaps": [
    {{
      "jd_requirement": "string — the skill or qualification from the JD",
      "jd_citation": "string — exact quote from the JD",
      "resume_evidence": "string or null — what the resume shows for this requirement, null if completely absent",
      "severity": "string — one of: missing, weak, strong",
      "rewrite_suggestions": [
        {{
          "before": "string — current resume text, or '[not present]' if the skill is missing entirely",
          "after": "string — suggested improved text the student can copy-paste"
        }}
      ]
    }}
  ],
  "overall_match_score": "integer 0-100 — how well the resume matches the JD overall",
  "summary": "string — 2-3 sentence executive summary of the match quality",
  "improvements_since_last_session": ["string — list of improvements noted"] or null
}}

Severity definitions:
- "missing": The JD requires this but the resume has ZERO evidence of it.
- "weak": The resume mentions it tangentially or lacks depth (e.g., listed as a skill but no project/experience using it).
- "strong": The resume clearly demonstrates this with projects, experience, or detailed descriptions.

Rules for rewrite_suggestions:
1. Each suggestion MUST be specific and actionable — NOT generic advice like "add more keywords" or "quantify your impact."
2. Provide exact phrasing the student can copy-paste into their resume.
3. For "strong" gaps, rewrite_suggestions should be an empty list [].
4. For "missing" gaps, the "before" field should be "[not present]" and "after" should suggest what to add and where.
5. For "weak" gaps, show the actual current resume text in "before" and the improved version in "after."
6. Provide 2-3 suggestions per gap (for missing/weak).
"""


def gap_analysis(
    parsed_jd: dict,
    parsed_resume: dict,
    prior_gaps: Optional[dict] = None,
) -> dict:
    """
    Perform gap analysis between JD requirements and resume.

    Args:
        parsed_jd: Output from parse_jd().
        parsed_resume: Output from parse_resume().
        prior_gaps: Previous gap analysis (from session memory) if available.

    Returns:
        Dict with gaps, overall_match_score, summary, improvements_since_last_session.
    """
    # Build the user prompt with all context
    prompt_parts = [
        "Perform a detailed gap analysis.\n",
        "=== JOB DESCRIPTION (PARSED) ===",
        json.dumps(parsed_jd, indent=2),
        "\n=== STUDENT RESUME (PARSED) ===",
        json.dumps(parsed_resume, indent=2),
    ]

    # If we have prior gap analysis (from session memory), include it
    if prior_gaps:
        prompt_parts.extend([
            "\n=== PRIOR GAP ANALYSIS (from previous session) ===",
            json.dumps(prior_gaps, indent=2),
            "\nIMPORTANT: Compare the current resume against the prior gap analysis. "
            "Note which gaps have been addressed (improved) and which remain. "
            "Populate 'improvements_since_last_session' with specific improvements detected.",
        ])
    else:
        prompt_parts.append(
            "\nThis is the student's first analysis — set 'improvements_since_last_session' to null."
        )

    user_prompt = '\n'.join(prompt_parts)

    result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        step_name="gap_analysis",
        response_format={"type": "json_object"},
    )

    # Log summary
    gaps = result.get("gaps", [])
    severity_counts = {"missing": 0, "weak": 0, "strong": 0}
    for gap in gaps:
        sev = gap.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    logger.info(
        f"[GAP_ANALYSIS] Score: {result.get('overall_match_score', '?')}/100 — "
        f"Missing: {severity_counts['missing']}, Weak: {severity_counts['weak']}, "
        f"Strong: {severity_counts['strong']}"
    )

    return result
