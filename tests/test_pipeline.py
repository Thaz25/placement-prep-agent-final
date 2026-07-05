"""
End-to-end pipeline tests using mock LLM responses.
Verifies the pipeline completes without errors and outputs valid structures.
"""

import os
import pytest
import tempfile
from pathlib import Path

# Force mock mode
os.environ["MOCK_MODE"] = "true"

from src.pipeline.parse_jd import parse_jd
from src.pipeline.parse_resume import parse_resume
from src.pipeline.gap_analysis import gap_analysis
from src.pipeline.practice_set import generate_practice_set
from src.pipeline.interview_questions import generate_interview_questions
from src.pipeline.compile_report import compile_report
from src.memory.session_store import SessionStore
from src.tools.problem_matcher import ProblemMatcher


class TestParseJD:
    """Test JD parsing step."""

    def test_parse_jd_returns_dict(self, sample_jd):
        result = parse_jd(sample_jd)
        assert isinstance(result, dict)

    def test_parse_jd_has_required_fields(self, sample_jd):
        result = parse_jd(sample_jd)
        required_fields = ["company", "role", "must_have_skills", "nice_to_have_skills",
                          "evaluation_focus", "role_level", "key_responsibilities"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_parse_jd_skills_have_citations(self, sample_jd):
        result = parse_jd(sample_jd)
        for skill in result.get("must_have_skills", []):
            assert "skill" in skill
            assert "jd_citation" in skill


class TestParseResume:
    """Test resume parsing step."""

    def test_parse_resume_returns_dict(self, sample_resume):
        result = parse_resume(sample_resume)
        assert isinstance(result, dict)

    def test_parse_resume_has_required_fields(self, sample_resume):
        result = parse_resume(sample_resume)
        required_fields = ["name", "skills", "projects", "education"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_parse_resume_skills_structured(self, sample_resume):
        result = parse_resume(sample_resume)
        skills = result.get("skills", {})
        assert "languages" in skills
        assert "frameworks" in skills


class TestGapAnalysis:
    """Test gap analysis step."""

    def test_gap_analysis_returns_dict(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        result = gap_analysis(jd, resume)
        assert isinstance(result, dict)

    def test_gap_analysis_has_required_fields(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        result = gap_analysis(jd, resume)
        assert "gaps" in result
        assert "overall_match_score" in result
        assert "summary" in result

    def test_gap_analysis_gaps_have_severity(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        result = gap_analysis(jd, resume)
        for gap in result.get("gaps", []):
            assert gap["severity"] in ("missing", "weak", "strong")

    def test_gap_analysis_score_in_range(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        result = gap_analysis(jd, resume)
        score = result.get("overall_match_score", -1)
        assert 0 <= score <= 100


class TestPracticeSet:
    """Test practice set generation."""

    def test_practice_set_returns_dict(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        gaps = gap_analysis(jd, resume)
        result = generate_practice_set(jd, gaps)
        assert isinstance(result, dict)

    def test_practice_set_has_topics(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        gaps = gap_analysis(jd, resume)
        result = generate_practice_set(jd, gaps)
        assert "focus_topics" in result
        assert "problems" in result


class TestInterviewQuestions:
    """Test interview question generation."""

    def test_interview_questions_returns_dict(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        gaps = gap_analysis(jd, resume)
        result = generate_interview_questions(jd, resume, gaps)
        assert isinstance(result, dict)

    def test_interview_questions_have_types(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        gaps = gap_analysis(jd, resume)
        result = generate_interview_questions(jd, resume, gaps)
        questions = result.get("questions", [])
        types = {q.get("type") for q in questions}
        assert "technical" in types
        assert "behavioral" in types


class TestCompileReport:
    """Test report compilation."""

    def test_compile_report_returns_dict(self, sample_jd, sample_resume):
        jd = parse_jd(sample_jd)
        resume = parse_resume(sample_resume)
        gaps = gap_analysis(jd, resume)
        practice = generate_practice_set(jd, gaps)
        interview = generate_interview_questions(jd, resume, gaps)
        result = compile_report(
            jd_raw=sample_jd, resume_raw=sample_resume,
            parsed_jd=jd, parsed_resume=resume,
            gap_analysis_result=gaps, practice_set=practice,
            interview_questions=interview,
        )
        assert isinstance(result, dict)
        assert "markdown_report" in result
        assert len(result["markdown_report"]) > 100


class TestProblemMatcher:
    """Test the problem matcher tool."""

    def test_matcher_loads_problems(self):
        matcher = ProblemMatcher()
        assert len(matcher.problems) > 0

    def test_matcher_filters_by_topic(self):
        matcher = ProblemMatcher()
        results = matcher.match_problems(topics=["arrays"], count=5)
        assert len(results) > 0
        for p in results:
            assert any(t in ["arrays", "two_pointers", "sliding_window"] for t in p.get("topics", []))

    def test_matcher_filters_by_difficulty(self):
        matcher = ProblemMatcher()
        results = matcher.match_problems(topics=["arrays"], difficulty_range=["Easy"], count=5)
        for p in results:
            assert p["difficulty"] == "Easy"

    def test_matcher_returns_limited_count(self):
        matcher = ProblemMatcher()
        results = matcher.match_problems(topics=["arrays", "strings", "trees"], count=3)
        assert len(results) <= 3

    def test_matcher_stats(self):
        matcher = ProblemMatcher()
        stats = matcher.get_stats()
        assert stats["total_problems"] > 100
        assert "by_difficulty" in stats


class TestSessionStore:
    """Test session memory."""

    def test_save_and_retrieve(self, sample_jd, sample_resume):
        # Use a temp database
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=Path(tmpdir) / "test.db")
            session_id = store.save_session(
                company="TestCo", role="SDE",
                jd_raw=sample_jd, resume_raw=sample_resume,
                jd_parsed={"test": True}, resume_parsed={"test": True},
                gap_analysis={"gaps": []}, practice_set={"problems": []},
                interview_questions={"questions": []}, overall_score=75,
            )
            assert session_id is not None

            retrieved = store.get_session(session_id)
            assert retrieved is not None
            assert retrieved["company"] == "TestCo"
            assert retrieved["overall_score"] == 75

    def test_find_prior_session(self, sample_jd, sample_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=Path(tmpdir) / "test.db")
            store.save_session(
                company="Unisys", role="SDE",
                jd_raw=sample_jd, resume_raw=sample_resume,
                jd_parsed={}, resume_parsed={},
                gap_analysis={"gaps": [{"severity": "missing"}]},
                practice_set={}, interview_questions={}, overall_score=50,
            )
            prior = store.find_prior_session("Unisys")
            assert prior is not None
            assert prior["company"] == "Unisys"

            # Case-insensitive match
            prior2 = store.find_prior_session("unisys")
            assert prior2 is not None

    def test_list_sessions(self, sample_jd, sample_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=Path(tmpdir) / "test.db")
            store.save_session(
                company="A", role="R", jd_raw="", resume_raw="",
                jd_parsed={}, resume_parsed={}, gap_analysis={},
                practice_set={}, interview_questions={}, overall_score=50,
            )
            store.save_session(
                company="B", role="R", jd_raw="", resume_raw="",
                jd_parsed={}, resume_parsed={}, gap_analysis={},
                practice_set={}, interview_questions={}, overall_score=80,
            )
            sessions = store.list_sessions()
            assert len(sessions) == 2

    def test_delete_session(self, sample_jd, sample_resume):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(db_path=Path(tmpdir) / "test.db")
            sid = store.save_session(
                company="Del", role="R", jd_raw="", resume_raw="",
                jd_parsed={}, resume_parsed={}, gap_analysis={},
                practice_set={}, interview_questions={}, overall_score=30,
            )
            assert store.delete_session(sid) is True
            assert store.get_session(sid) is None
