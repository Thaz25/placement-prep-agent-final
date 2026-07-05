"""
Step 4: Generate Practice Set — Hybrid LLM + local dataset tool call.
"""

import json
import logging
from typing import Optional

from src import config
from src.llm_client import call_llm
from src.tools.problem_matcher import ProblemMatcher

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert coding interview preparation advisor.
Based on a job description's evaluation focus and identified gaps, recommend practice topics.

{config.GROUNDING_INSTRUCTION}

You MUST respond with valid JSON matching this exact schema:
{{
  "focus_topics": [
    {{
      "topic": "string — one of: arrays_strings, linked_lists, trees_graphs, dynamic_programming, sorting_searching, stacks_queues, hash_maps, recursion_backtracking, greedy, math_bit_manipulation, sql, system_design, oop_design_patterns, os_networking, behavioral",
      "priority": "string — high or medium",
      "reasoning": "string — why this topic matters for THIS specific JD"
    }}
  ],
  "study_order_suggestion": "string — recommended order and timeline for practicing these topics"
}}

Rules:
1. Recommend 5-8 topics, ordered by priority (high first).
2. Topics marked "high" should directly correspond to must-have JD skills or identified gaps.
3. Topics marked "medium" are nice-to-have or generally important for the role level.
4. The reasoning should cite specific JD requirements or identified gaps.
5. study_order_suggestion should be practical — assume 2-3 weeks of preparation time.
"""


def generate_practice_set(
    parsed_jd: dict,
    gap_analysis_result: dict,
    role_level: str = "entry",
    focus_preference: Optional[str] = None,
) -> dict:
    """
    Generate a tailored practice set using LLM topic analysis + local problem database.

    Args:
        parsed_jd: Output from parse_jd().
        gap_analysis_result: Output from gap_analysis().
        role_level: "intern", "entry", "mid", or "senior".
        focus_preference: Optional user preference — "DSA", "system_design", "behavioral", or "mixed".

    Returns:
        Dict with focus_topics, problems, and study_order_suggestion.
    """
    # ─── Step 4a: LLM identifies priority topics ─────────────────
    prompt_parts = [
        "Recommend practice topics for this job preparation.\n",
        "=== JD EVALUATION FOCUS ===",
        json.dumps(parsed_jd.get("evaluation_focus", {}), indent=2),
        "\n=== IDENTIFIED GAPS (skills the student is missing or weak in) ===",
        json.dumps(
            [
                {"requirement": g["jd_requirement"], "severity": g["severity"]}
                for g in gap_analysis_result.get("gaps", [])
                if g.get("severity") in ("missing", "weak")
            ],
            indent=2,
        ),
        f"\nRole level: {role_level}",
    ]

    if focus_preference and focus_preference != "mixed":
        prompt_parts.append(
            f"\nStudent's preferred focus area: {focus_preference}. "
            "Weight recommendations toward this area, but don't ignore critical gaps."
        )

    user_prompt = '\n'.join(prompt_parts)

    topic_result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        step_name="practice_set",
        response_format={"type": "json_object"},
    )

    # ─── Step 4b: Query local problem database (TOOL CALL) ──────
    matcher = ProblemMatcher()

    # Extract topic names from LLM result
    focus_topics = topic_result.get("focus_topics", [])
    topic_names = [t["topic"] for t in focus_topics]

    # Map role level to difficulty range
    difficulty_map = {
        "intern": ["Easy", "Medium"],
        "entry": ["Easy", "Medium"],
        "mid": ["Medium", "Hard"],
        "senior": ["Medium", "Hard"],
    }
    difficulty_range = difficulty_map.get(role_level, ["Easy", "Medium"])

    # Query the local dataset
    matched_problems = matcher.match_problems(
        topics=topic_names,
        difficulty_range=difficulty_range,
        count=config.MAX_PROBLEMS_IN_SET,
    )

    logger.info(
        f"[PRACTICE_SET] LLM identified {len(focus_topics)} topics, "
        f"matcher returned {len(matched_problems)} problems"
    )

    # ─── Step 4c: LLM generates reasons for each problem ────────
    if matched_problems and not config.MOCK_MODE and config.API_KEY:
        reason_prompt = (
            "For each practice problem below, write a one-line reason why it was selected "
            "for THIS specific job preparation. Reference the JD requirement or gap it addresses.\n\n"
            f"JD Role: {parsed_jd.get('role', 'Software Engineer')}\n"
            f"Key gaps: {', '.join(topic_names[:5])}\n\n"
            "Problems:\n"
            + '\n'.join(
                f"- {p['title']} ({p['difficulty']}, topics: {', '.join(p['topics'])})"
                for p in matched_problems
            )
            + "\n\nRespond with JSON: {\"reasons\": {\"Problem Title\": \"reason string\", ...}}"
        )

        try:
            reasons_result = call_llm(
                system_prompt="You generate concise, JD-specific reasons for practice problem selections.",
                user_prompt=reason_prompt,
                step_name="practice_reasons",
                response_format={"type": "json_object"},
            )
            reasons = reasons_result.get("reasons", {})
        except Exception:
            reasons = {}

        # Attach reasons to problems
        for problem in matched_problems:
            problem["reason_selected"] = reasons.get(
                problem["title"],
                f"Matches JD focus area: {', '.join(problem.get('topics', []))}"
            )
    else:
        # Mock mode — add generic reasons
        for problem in matched_problems:
            problem["reason_selected"] = f"Matches JD focus area: {', '.join(problem.get('topics', []))}"

    return {
        "focus_topics": focus_topics,
        "problems": matched_problems,
        "study_order_suggestion": topic_result.get(
            "study_order_suggestion",
            "Start with high-priority topics and work through medium-priority ones over 2-3 weeks."
        ),
    }
