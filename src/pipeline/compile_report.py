"""
Step 6: Compile Report — Assemble all pipeline outputs into a downloadable prep kit.
No LLM call — pure data assembly.
"""

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def compile_report(
    jd_raw: str,
    resume_raw: str,
    parsed_jd: dict,
    parsed_resume: dict,
    gap_analysis_result: dict,
    practice_set: dict,
    interview_questions: dict,
    company_name: Optional[str] = None,
) -> dict:
    """
    Compile all pipeline outputs into a unified report.

    Args:
        All outputs from the previous pipeline steps.

    Returns:
        Dict with the full report data and a rendered Markdown string.
    """
    company = company_name or parsed_jd.get("company", "Not Specified")
    role = parsed_jd.get("role", "Software Engineer")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ─── Build Markdown Report ────────────────────────────────────
    md_parts = [
        f"# 🎯 Placement Prep Kit",
        f"**Company:** {company}  ",
        f"**Role:** {role}  ",
        f"**Generated:** {timestamp}  ",
        f"**Match Score:** {gap_analysis_result.get('overall_match_score', 'N/A')}/100",
        "",
        "---",
        "",
        "## 📋 JD Breakdown",
        "",
        "### Must-Have Skills",
    ]

    for skill in parsed_jd.get("must_have_skills", []):
        md_parts.append(
            f"- **{skill['skill']}** — _\"{skill['jd_citation']}\"_ (Line {skill.get('line_number', '?')})"
        )

    md_parts.extend(["", "### Nice-to-Have Skills"])
    for skill in parsed_jd.get("nice_to_have_skills", []):
        md_parts.append(
            f"- **{skill['skill']}** — _\"{skill['jd_citation']}\"_ (Line {skill.get('line_number', '?')})"
        )

    eval_focus = parsed_jd.get("evaluation_focus", {})
    md_parts.extend([
        "",
        "### Evaluation Focus",
        f"**Primary Areas:** {', '.join(eval_focus.get('primary_areas', []))}",
        f"**Reasoning:** {eval_focus.get('reasoning', 'N/A')}",
        "",
    ])

    # ─── Gap Analysis Section ─────────────────────────────────────
    md_parts.extend([
        "---",
        "",
        "## 🔍 Resume Gap Analysis",
        "",
        f"**Overall Match Score: {gap_analysis_result.get('overall_match_score', 'N/A')}/100**",
        "",
        f"_{gap_analysis_result.get('summary', '')}_",
        "",
    ])

    # Improvements since last session
    improvements = gap_analysis_result.get("improvements_since_last_session")
    if improvements:
        md_parts.extend([
            "### ✅ Improvements Since Last Session",
            "",
        ])
        for imp in improvements:
            md_parts.append(f"- {imp}")
        md_parts.append("")

    # Gap details
    severity_emoji = {"missing": "🔴", "weak": "🟡", "strong": "🟢"}
    for gap in gap_analysis_result.get("gaps", []):
        sev = gap.get("severity", "unknown")
        emoji = severity_emoji.get(sev, "⚪")
        md_parts.extend([
            f"### {emoji} {gap['jd_requirement']} — {sev.upper()}",
            f"**JD says:** _\"{gap['jd_citation']}\"_  ",
            f"**Resume shows:** {gap.get('resume_evidence') or '_Not found in resume_'}",
            "",
        ])
        if gap.get("rewrite_suggestions"):
            md_parts.append("**Suggested rewrites:**")
            for i, sugg in enumerate(gap["rewrite_suggestions"], 1):
                md_parts.extend([
                    f"  {i}. **Before:** {sugg['before']}",
                    f"     **After:** {sugg['after']}",
                    "",
                ])

    # ─── Practice Set Section ─────────────────────────────────────
    md_parts.extend([
        "---",
        "",
        "## 💻 Tailored Practice Set",
        "",
        "### Focus Topics",
    ])
    for topic in practice_set.get("focus_topics", []):
        priority_badge = "🔥" if topic.get("priority") == "high" else "📌"
        md_parts.append(
            f"- {priority_badge} **{topic['topic']}** ({topic.get('priority', 'medium')}) — {topic.get('reasoning', '')}"
        )

    md_parts.extend(["", "### Practice Problems", ""])
    md_parts.append("| # | Problem | Difficulty | Topics | Why Selected |")
    md_parts.append("|---|---------|------------|--------|--------------|")
    for i, prob in enumerate(practice_set.get("problems", []), 1):
        title = prob.get("title", "Unknown")
        url = prob.get("url", "#")
        diff = prob.get("difficulty", "?")
        topics = ", ".join(prob.get("topics", []))
        reason = prob.get("reason_selected", "")
        md_parts.append(f"| {i} | [{title}]({url}) | {diff} | {topics} | {reason} |")

    md_parts.extend([
        "",
        f"**Study Plan:** {practice_set.get('study_order_suggestion', 'N/A')}",
        "",
    ])

    # ─── Interview Questions Section ──────────────────────────────
    md_parts.extend([
        "---",
        "",
        "## 🎤 Mock Interview Questions",
        "",
    ])
    for i, q in enumerate(interview_questions.get("questions", []), 1):
        q_type = q.get("type", "unknown")
        badge = "🔧" if q_type == "technical" else "💬"
        md_parts.extend([
            f"### {badge} Q{i}. {q['question']}",
            f"**Type:** {q_type.capitalize()} | **Probes:** {q.get('targets', 'N/A')}  ",
            f"**Based on:** _\"{q.get('citation', 'N/A')}\"_  ",
            f"**Approach hint:** {q.get('suggested_approach', 'N/A')}",
            "",
        ])

    # ─── Footer ───────────────────────────────────────────────────
    md_parts.extend([
        "---",
        "",
        f"_Generated by Placement Prep Agent on {timestamp}_",
    ])

    markdown_report = '\n'.join(md_parts)

    report = {
        "company": company,
        "role": role,
        "timestamp": timestamp,
        "overall_score": gap_analysis_result.get("overall_match_score", 0),
        "parsed_jd": parsed_jd,
        "parsed_resume": parsed_resume,
        "gap_analysis": gap_analysis_result,
        "practice_set": practice_set,
        "interview_questions": interview_questions,
        "markdown_report": markdown_report,
    }

    logger.info(
        f"[COMPILE_REPORT] Report compiled for {company} — {role} "
        f"(score: {report['overall_score']}/100)"
    )

    return report
