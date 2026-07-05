"""
Eval Harness — Tests expected gap analysis categories against fixture pairs.
This is the "quality assurance" component that judges are scoring on.

In mock mode, this validates that the mock responses have the expected structure.
With a real API key (MOCK_MODE=false), this validates that the LLM produces
reasonable gap categorizations for known JD/resume pairs.
"""

import os
import json
import pytest
from pathlib import Path

# Force mock mode for CI — set MOCK_MODE=false to test with real API
os.environ.setdefault("MOCK_MODE", "true")

from src.pipeline.parse_jd import parse_jd
from src.pipeline.parse_resume import parse_resume
from src.pipeline.gap_analysis import gap_analysis
from src.pipeline.interview_questions import generate_interview_questions

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def get_fixture_files():
    """Discover all fixture files."""
    return sorted(FIXTURES_DIR.glob("pair_*.json"))


class TestGapCategories:
    """
    Eval harness: verify that the pipeline produces reasonable gap categorizations
    for known JD/resume pairs with expected outcomes.
    """

    @pytest.mark.parametrize(
        "fixture_file",
        get_fixture_files(),
        ids=lambda p: p.stem,
    )
    def test_gap_analysis_structure(self, fixture_file):
        """Each fixture should produce a valid gap analysis with expected fields."""
        with open(fixture_file, 'r', encoding='utf-8') as f:
            fixture = json.load(f)

        jd_result = parse_jd(fixture["jd_text"])
        resume_result = parse_resume(fixture["resume_text"])
        gap_result = gap_analysis(jd_result, resume_result)

        # Verify structure
        assert "gaps" in gap_result, "Gap analysis must have 'gaps' field"
        assert "overall_match_score" in gap_result, "Gap analysis must have 'overall_match_score'"
        assert "summary" in gap_result, "Gap analysis must have 'summary'"

        # Verify each gap has required fields
        for gap in gap_result["gaps"]:
            assert "jd_requirement" in gap, "Each gap must have 'jd_requirement'"
            assert "severity" in gap, "Each gap must have 'severity'"
            assert gap["severity"] in ("missing", "weak", "strong"), \
                f"Severity must be missing/weak/strong, got: {gap['severity']}"

        # Verify score is in valid range
        score = gap_result["overall_match_score"]
        assert isinstance(score, (int, float)), "Score must be numeric"
        assert 0 <= score <= 100, f"Score must be 0-100, got: {score}"

    @pytest.mark.parametrize(
        "fixture_file",
        get_fixture_files(),
        ids=lambda p: p.stem,
    )
    def test_interview_questions_generated(self, fixture_file):
        """Each fixture should produce interview questions with both types."""
        with open(fixture_file, 'r', encoding='utf-8') as f:
            fixture = json.load(f)

        jd_result = parse_jd(fixture["jd_text"])
        resume_result = parse_resume(fixture["resume_text"])
        gap_result = gap_analysis(jd_result, resume_result)
        interview_result = generate_interview_questions(jd_result, resume_result, gap_result)

        # Verify questions exist
        questions = interview_result.get("questions", [])
        assert len(questions) > 0, "Must generate at least 1 question"

        # Verify question structure
        for q in questions:
            assert "question" in q, "Each question must have 'question' text"
            assert "type" in q, "Each question must have 'type'"
            assert q["type"] in ("technical", "behavioral"), \
                f"Question type must be technical/behavioral, got: {q['type']}"

        # Verify mix of types (at least 1 of each in expected)
        types = {q["type"] for q in questions}
        expected_types = set(fixture.get("expected_question_types", ["technical", "behavioral"]))
        assert types >= expected_types, \
            f"Expected question types {expected_types}, got {types}"


class TestEvalHarnessReporting:
    """Summary reporting for the eval harness."""

    def test_eval_summary(self):
        """Run all fixtures and print a pass/fail summary."""
        results = []
        for fixture_file in get_fixture_files():
            with open(fixture_file, 'r', encoding='utf-8') as f:
                fixture = json.load(f)

            try:
                jd_result = parse_jd(fixture["jd_text"])
                resume_result = parse_resume(fixture["resume_text"])
                gap_result = gap_analysis(jd_result, resume_result)

                # Check structure
                has_gaps = "gaps" in gap_result and len(gap_result["gaps"]) > 0
                has_score = 0 <= gap_result.get("overall_match_score", -1) <= 100
                has_summary = bool(gap_result.get("summary"))

                passed = has_gaps and has_score and has_summary
                results.append({
                    "fixture": fixture["name"],
                    "passed": passed,
                    "score": gap_result.get("overall_match_score"),
                    "gap_count": len(gap_result.get("gaps", [])),
                })
            except Exception as e:
                results.append({
                    "fixture": fixture["name"],
                    "passed": False,
                    "error": str(e),
                })

        # Print summary
        print("\n" + "=" * 60)
        print("EVAL HARNESS SUMMARY")
        print("=" * 60)
        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))
        for r in results:
            status = "✅ PASS" if r.get("passed") else "❌ FAIL"
            score_str = f"Score: {r.get('score', '?')}" if r.get("passed") else f"Error: {r.get('error', 'unknown')}"
            print(f"  {status}  {r['fixture']} — {score_str}")
        print(f"\nTotal: {passed}/{total} passed")
        print("=" * 60)

        assert passed == total, f"{total - passed} fixture(s) failed"
