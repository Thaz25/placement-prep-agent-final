"""
Step 2: Parse Resume — Extract structured data from raw resume text.
"""

import json
import logging

from src import config
from src.llm_client import call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert resume analyst for placement preparation.
Your task is to extract structured information from a student's resume.

{config.GROUNDING_INSTRUCTION}

You MUST respond with valid JSON matching this exact schema:
{{
  "name": "string — candidate's full name",
  "skills": {{
    "languages": ["string — programming languages"],
    "frameworks": ["string — frameworks and libraries"],
    "tools": ["string — development tools, platforms"],
    "concepts": ["string — CS concepts, methodologies"]
  }},
  "projects": [
    {{
      "name": "string — project title",
      "tech_stack": ["string — technologies used"],
      "description": "string — brief description of what the project does"
    }}
  ],
  "experience": [
    {{
      "role": "string — job title / internship title",
      "company": "string — company or organization name",
      "duration": "string — e.g. 'Jun 2024 - Aug 2024'",
      "highlights": ["string — key achievements or responsibilities"]
    }}
  ],
  "education": {{
    "degree": "string — e.g. 'B.Tech Computer Science'",
    "institution": "string — university/college name",
    "gpa": "string — GPA or percentage if mentioned, else 'Not specified'"
  }},
  "certifications": ["string — certification names"],
  "achievements": ["string — hackathons, awards, competitive programming, etc."]
}}

Rules:
1. Extract ONLY what is explicitly written in the resume. Do not infer or add skills not mentioned.
2. For projects, capture the actual tech stack used, not assumed technologies.
3. If a section is empty or not present in the resume, use an empty list [] or appropriate default.
4. Keep descriptions factual and concise — use the resume's own language where possible.
"""


def parse_resume(resume_text: str) -> dict:
    """
    Parse a resume into structured format.

    Args:
        resume_text: Raw resume text.

    Returns:
        Dict with name, skills, projects, experience, education,
        certifications, achievements.
    """
    user_prompt = f"Extract structured data from this resume:\n\n{resume_text}"

    result = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        step_name="parse_resume",
        response_format={"type": "json_object"},
    )

    logger.info(
        f"[PARSE_RESUME] Extracted profile for '{result.get('name', 'Unknown')}' — "
        f"{len(result.get('projects', []))} projects, "
        f"{len(result.get('experience', []))} experiences"
    )

    return result
