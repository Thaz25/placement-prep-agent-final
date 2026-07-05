"""
LLM Client — Grok (xAI) API wrapper using OpenAI-compatible SDK.
Supports mock mode for development/testing without an API key.
"""

import json
import time
import logging
from typing import Optional

from src import config

logger = logging.getLogger(__name__)

# ─── Mock Responses ───────────────────────────────────────────────────
# Used when MOCK_MODE=true or API key is not set

MOCK_RESPONSES = {
    "parse_jd": {
        "company": "Acme Corp",
        "role": "Software Development Engineer",
        "must_have_skills": [
            {"skill": "Python", "jd_citation": "Strong proficiency in Python", "line_number": 5},
            {"skill": "REST APIs", "jd_citation": "Experience building RESTful APIs", "line_number": 8},
            {"skill": "SQL", "jd_citation": "Solid understanding of SQL databases", "line_number": 9},
            {"skill": "Data Structures", "jd_citation": "Strong foundation in data structures and algorithms", "line_number": 12},
        ],
        "nice_to_have_skills": [
            {"skill": "Docker", "jd_citation": "Familiarity with containerization (Docker)", "line_number": 15},
            {"skill": "AWS", "jd_citation": "Experience with cloud platforms preferred", "line_number": 16},
        ],
        "evaluation_focus": {
            "primary_areas": ["arrays_strings", "sql_databases", "api_design"],
            "reasoning": "The JD emphasizes backend development with Python and SQL, suggesting coding tests will focus on data manipulation, array/string problems, and API design patterns.",
            "supporting_citations": [
                "Strong foundation in data structures and algorithms",
                "Experience building RESTful APIs",
                "Solid understanding of SQL databases",
            ],
        },
        "role_level": "entry",
        "key_responsibilities": [
            "Develop and maintain backend services",
            "Write clean, testable code",
            "Collaborate with cross-functional teams",
        ],
    },
    "parse_resume": {
        "name": "Pranav N",
        "skills": {
            "languages": ["Python", "JavaScript", "C++"],
            "frameworks": ["React", "Node.js", "Flask"],
            "tools": ["Git", "VS Code", "Postman"],
            "concepts": ["OOP", "Data Structures", "Web Development"],
        },
        "projects": [
            {
                "name": "Blockchain Voting Platform",
                "tech_stack": ["Solidity", "React", "Hardhat"],
                "description": "Decentralized voting platform built on Ethereum blockchain",
            },
            {
                "name": "Weather Dashboard",
                "tech_stack": ["Python", "Flask", "Chart.js"],
                "description": "Real-time weather data visualization dashboard",
            },
        ],
        "experience": [],
        "education": {
            "degree": "B.Tech Computer Science",
            "institution": "University XYZ",
            "gpa": "8.5/10",
        },
        "certifications": [],
        "achievements": ["Smart India Hackathon Finalist"],
    },
    "gap_analysis": {
        "gaps": [
            {
                "jd_requirement": "REST API Development",
                "jd_citation": "Experience building RESTful APIs",
                "resume_evidence": "Flask mentioned in projects but no explicit API work described",
                "severity": "weak",
                "rewrite_suggestions": [
                    {
                        "before": "Weather Dashboard — Python, Flask, Chart.js",
                        "after": "Weather Dashboard — Built RESTful API endpoints with Flask serving real-time weather data to a Chart.js frontend; handled JSON serialization, error responses, and rate limiting",
                    },
                    {
                        "before": "[not present]",
                        "after": "Skills: REST API Design, API Authentication (JWT/OAuth), Swagger/OpenAPI Documentation",
                    },
                ],
            },
            {
                "jd_requirement": "SQL Databases",
                "jd_citation": "Solid understanding of SQL databases",
                "resume_evidence": None,
                "severity": "missing",
                "rewrite_suggestions": [
                    {
                        "before": "[not present]",
                        "after": "Skills: PostgreSQL, MySQL, SQL Query Optimization, Database Schema Design",
                    },
                    {
                        "before": "[not present]",
                        "after": "Add a project: 'Student Management System — Designed normalized database schema in PostgreSQL with complex JOIN queries, indexing, and transaction management'",
                    },
                ],
            },
            {
                "jd_requirement": "Python Proficiency",
                "jd_citation": "Strong proficiency in Python",
                "resume_evidence": "Python listed in skills and used in Weather Dashboard project",
                "severity": "strong",
                "rewrite_suggestions": [],
            },
            {
                "jd_requirement": "Data Structures & Algorithms",
                "jd_citation": "Strong foundation in data structures and algorithms",
                "resume_evidence": "Data Structures listed under concepts",
                "severity": "weak",
                "rewrite_suggestions": [
                    {
                        "before": "Concepts: OOP, Data Structures, Web Development",
                        "after": "Concepts: OOP, Data Structures & Algorithms (Arrays, Trees, Graphs, Dynamic Programming), System Design Fundamentals, Web Development",
                    },
                ],
            },
            {
                "jd_requirement": "Docker / Containerization",
                "jd_citation": "Familiarity with containerization (Docker)",
                "resume_evidence": None,
                "severity": "missing",
                "rewrite_suggestions": [
                    {
                        "before": "[not present]",
                        "after": "Tools: Docker, Docker Compose — containerized Flask application for consistent development and deployment environments",
                    },
                ],
            },
        ],
        "overall_match_score": 52,
        "summary": "The resume shows a solid Python foundation and relevant project experience, but lacks explicit SQL database work and REST API experience. The Data Structures mention needs strengthening with specific algorithm knowledge. Docker/containerization is completely absent.",
        "improvements_since_last_session": None,
    },
    "interview_questions": {
        "questions": [
            {
                "question": "Walk me through how you would design a RESTful API for a voting system. What endpoints would you create, and how would you handle authentication?",
                "type": "technical",
                "targets": "REST API Design + Blockchain Voting Platform project",
                "citation": "Experience building RESTful APIs",
                "suggested_approach": "Start with resource identification (voters, candidates, elections), define CRUD endpoints, discuss authentication (JWT), then touch on your blockchain project as a real example.",
            },
            {
                "question": "Given an array of integers representing votes for different candidates, find the candidate with the majority vote (more than n/2 occurrences). What's the most efficient approach?",
                "type": "technical",
                "targets": "Data Structures & Algorithms evaluation",
                "citation": "Strong foundation in data structures and algorithms",
                "suggested_approach": "Discuss Boyer-Moore majority vote algorithm (O(n) time, O(1) space). Mention the brute force and hash map approaches first to show progression.",
            },
            {
                "question": "Write a SQL query to find the top 3 most active users in a system, along with their total number of transactions in the last 30 days.",
                "type": "technical",
                "targets": "SQL proficiency (identified gap)",
                "citation": "Solid understanding of SQL databases",
                "suggested_approach": "Use GROUP BY with COUNT, WHERE clause for date filtering, ORDER BY DESC with LIMIT. Mention window functions as an alternative.",
            },
            {
                "question": "Tell me about a time when you had to learn a completely new technology under a tight deadline. How did you approach it?",
                "type": "behavioral",
                "targets": "Learning agility — relevant to the Blockchain Voting project",
                "citation": "Blockchain Voting Platform project using Solidity",
                "suggested_approach": "Use STAR format. Reference learning Solidity/blockchain for your voting platform. Emphasize structured learning approach, resource selection, and the outcome.",
            },
            {
                "question": "How would you handle a situation where your code passes all tests locally but fails in production?",
                "type": "behavioral",
                "targets": "Debugging methodology + production awareness",
                "citation": "Write clean, testable code",
                "suggested_approach": "Discuss systematic debugging: check environment differences, review logs, reproduce with production data, then mention Docker as a solution for environment parity.",
            },
            {
                "question": "Explain the difference between a hash map and a binary search tree. When would you choose one over the other?",
                "type": "technical",
                "targets": "Data Structures conceptual depth",
                "citation": "Strong foundation in data structures and algorithms",
                "suggested_approach": "Compare time complexities (O(1) avg vs O(log n)), discuss ordered vs unordered access patterns, mention real-world use cases like database indexing.",
            },
            {
                "question": "Describe how you collaborated with your team on the Blockchain Voting Platform. What was your specific role and contribution?",
                "type": "behavioral",
                "targets": "Teamwork + technical contribution clarity",
                "citation": "Collaborate with cross-functional teams",
                "suggested_approach": "Be specific about YOUR contributions (smart contract logic, frontend, testing). Show awareness of team dynamics and how you resolved disagreements.",
            },
            {
                "question": "Design a simple URL shortening service. Walk me through the database schema, the API, and how you'd handle high traffic.",
                "type": "technical",
                "targets": "System design thinking (overall engineering maturity)",
                "citation": "Develop and maintain backend services",
                "suggested_approach": "Start simple: table with (short_code, long_url, created_at), hash-based generation, GET redirect endpoint. Then discuss caching (Redis), horizontal scaling, and analytics.",
            },
        ],
    },
    "practice_set": {
        "focus_topics": [
            {"topic": "arrays_strings", "priority": "high", "reasoning": "Core DSA area emphasized in JD's algorithms requirement"},
            {"topic": "sql", "priority": "high", "reasoning": "SQL databases are a must-have skill — identified as a gap"},
            {"topic": "hash_maps", "priority": "high", "reasoning": "Fundamental to efficient problem solving, tested heavily in coding rounds"},
            {"topic": "api_design", "priority": "medium", "reasoning": "REST API experience is required — practice system design patterns"},
            {"topic": "trees", "priority": "medium", "reasoning": "Common in coding interviews for entry-level SDE roles"},
        ],
        "problems": [],  # Will be filled by problem_matcher
        "study_order_suggestion": "Start with Arrays & Hash Maps (week 1), then SQL problems (week 1-2), then move to Trees and API design patterns (week 2-3). Focus on medium difficulty — easy problems build confidence but medium problems are what you'll face in the actual test.",
    },
}


def _get_client():
    """Lazily initialize the OpenAI-compatible client for Grok."""
    from openai import OpenAI

    if not config.API_KEY:
        raise ValueError(
            "XAI_API_KEY is not set. Please add it to your .env file or Streamlit secrets. "
            "Get your key from https://console.x.ai"
        )
    return OpenAI(
        api_key=config.API_KEY,
        base_url=config.BASE_URL,
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    step_name: str = "unknown",
    response_format: Optional[dict] = None,
) -> dict | str:
    """
    Call the Grok LLM via OpenAI-compatible API.
    
    Args:
        system_prompt: The system instruction for the LLM.
        user_prompt: The user's input text.
        step_name: Pipeline step name (for logging and mock routing).
        response_format: If set to {"type": "json_object"}, forces JSON output.
    
    Returns:
        Parsed JSON dict if response_format is json, else raw string.
    """
    # ─── Mock Mode ────────────────────────────────────────────────
    if config.MOCK_MODE or not config.API_KEY:
        logger.info(f"[MOCK] Returning mock response for step: {step_name}")
        mock = MOCK_RESPONSES.get(step_name, {"mock": True, "step": step_name})
        return mock

    # ─── Real API Call ────────────────────────────────────────────
    client = _get_client()
    last_error = None

    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            kwargs = {
                "model": config.MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": config.LLM_TEMPERATURE,
                "max_tokens": config.LLM_MAX_TOKENS,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content

            # Log token usage
            if response.usage:
                logger.info(
                    f"[LLM] Step '{step_name}' — "
                    f"prompt_tokens={response.usage.prompt_tokens}, "
                    f"completion_tokens={response.usage.completion_tokens}, "
                    f"total_tokens={response.usage.total_tokens}"
                )

            # Parse JSON if requested
            if response_format and response_format.get("type") == "json_object":
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"[LLM] JSON parse failed for step '{step_name}', returning raw")
                    return {"raw_response": content, "parse_error": True}

            return content

        except Exception as e:
            last_error = e
            wait_time = config.LLM_RETRY_DELAY * (2 ** attempt)
            logger.warning(
                f"[LLM] Attempt {attempt + 1}/{config.LLM_MAX_RETRIES} failed for "
                f"step '{step_name}': {e}. Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)

    raise RuntimeError(
        f"LLM call failed after {config.LLM_MAX_RETRIES} attempts for step '{step_name}': {last_error}"
    )
