"""
Step 5: Generate Mock Interview Questions — Technical + Behavioral.
"""

import json
import logging

from src import config
from src.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert mock interviewer for campus placements.
Generate interview questions that probe specific JD requirements and resume claims.

{config.GROUNDING_INSTRUCTION}

You MUST respond with valid JSON matching this exact schema:
{{
  "questions": [
    {{
      "question": "string — the full interview question",
      "type": "string — 'technical' or 'behavioral'",
      "targets": "string — what JD requirement or resume element this question probes",
      "citation": "string — exact quote from the JD or resume that motivated this question",
      "suggested_approach": "string — 2-3 sentence hint for how the student should approach this"
    }}
  ]
}}

Rules:
1. Generate {config.MIN_INTERVIEW_QUESTIONS}-{config.MAX_INTERVIEW_QUESTIONS} questions total.
2. Split approximately 60% technical, 40% behavioral.
3. EVERY question must be tied to a SPECIFIC JD requirement or resume claim — no generic questions.
4. Technical questions should test the actual skill level needed (don't ask senior-level system design for an intern role).
5. Behavioral questions should probe the student's claimed experiences — ask about THEIR specific projects.
6. For identified gaps (missing/weak skills), include questions that test those areas — the student needs to practice these most.
7. Include the suggested_approach as a coaching aid — be specific, not generic.
8. Vary difficulty: include some approachable questions and some challenging ones.
"""


def generate_interview_questions(
    parsed_jd: dict,
    parsed_resume: dict,
    gap_analysis_result: dict,
) -> dict:
    """
    Generate mock interview questions tied to JD requirements and resume.

    Args:
        parsed_jd: Output from parse_jd().
        parsed_resume: Output from parse_resume().
        gap_analysis_result: Output from gap_analysis().

    Returns:
        Dict with list of questions, each with type, targets, citation, suggested_approach.
    """
    user_prompt = '\n'.join([
        "Generate mock interview questions for this candidate/role combination.\n",
        "=== JOB DESCRIPTION (PARSED) ===",
        json.dumps(parsed_jd, indent=2),
        "\n=== STUDENT RESUME (PARSED) ===",
        json.dumps(parsed_resume, indent=2),
        "\n=== GAP ANALYSIS RESULTS ===",
        json.dumps(gap_analysis_result, indent=2),
        "\nFocus especially on gaps marked 'missing' or 'weak' — "
        "these are the areas the student will struggle most in interviews.",
    ])

    result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        step_name="interview_questions",
        response_format={"type": "json_object"},
    )

    questions = result.get("questions", [])
    tech_count = sum(1 for q in questions if q.get("type") == "technical")
    behav_count = sum(1 for q in questions if q.get("type") == "behavioral")

    logger.info(
        f"[INTERVIEW_QS] Generated {len(questions)} questions — "
        f"{tech_count} technical, {behav_count} behavioral"
    )

    return result
