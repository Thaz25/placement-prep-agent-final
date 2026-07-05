"""
Step 1: Parse Job Description — Extract structured data from raw JD text.
"""

import json
import logging

from src import config
from src.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert job description analyst for placement preparation.
Your task is to extract structured information from a job description (JD).

{config.GROUNDING_INSTRUCTION}

You MUST respond with valid JSON matching this exact schema:
{{
  "company": "string — company name if mentioned, else 'Not Specified'",
  "role": "string — exact role title",
  "must_have_skills": [
    {{
      "skill": "string — skill name",
      "jd_citation": "string — exact quote from the JD that mentions this skill",
      "line_number": "integer — approximate line number in the JD"
    }}
  ],
  "nice_to_have_skills": [
    {{
      "skill": "string",
      "jd_citation": "string — exact quote",
      "line_number": "integer"
    }}
  ],
  "evaluation_focus": {{
    "primary_areas": ["string — e.g. 'arrays_strings', 'system_design', 'sql_databases', 'dynamic_programming'"],
    "reasoning": "string — explain WHY you inferred these focus areas from the JD",
    "supporting_citations": ["string — exact JD quotes supporting each inference"]
  }},
  "role_level": "string — one of: intern, entry, mid, senior",
  "key_responsibilities": ["string — each responsibility from the JD"]
}}

Rules:
1. For must_have_skills, include ONLY skills explicitly required (marked with "required", "must have", or clearly stated as mandatory).
2. For nice_to_have_skills, include skills marked as "preferred", "bonus", "nice to have", or similar.
3. For evaluation_focus, INFER what coding tests and interviews likely focus on based on the skills and responsibilities. Map to standard DSA/CS categories.
4. Always include the exact JD text as citations — do not paraphrase.
5. If the JD doesn't specify a company name, use "Not Specified".
"""


def parse_jd(jd_text: str) -> dict:
    """
    Parse a job description into structured format.

    Args:
        jd_text: Raw job description text.

    Returns:
        Dict with company, role, must_have_skills, nice_to_have_skills,
        evaluation_focus, role_level, key_responsibilities.
    """
    # Add line numbers to help the LLM cite accurately
    numbered_lines = []
    for i, line in enumerate(jd_text.strip().split('\n'), 1):
        numbered_lines.append(f"[Line {i}] {line}")
    numbered_jd = '\n'.join(numbered_lines)

    user_prompt = f"Analyze this job description and extract structured data:\n\n{numbered_jd}"

    result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        step_name="parse_jd",
        response_format={"type": "json_object"},
    )

    logger.info(f"[PARSE_JD] Extracted {len(result.get('must_have_skills', []))} must-have skills, "
                f"{len(result.get('nice_to_have_skills', []))} nice-to-have skills")

    return result
