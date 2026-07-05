"""
Shared pytest fixtures for Placement Prep Agent tests.
"""

import json
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force mock mode for tests
os.environ["MOCK_MODE"] = "true"

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def load_fixture():
    """Factory fixture that loads a test pair by filename."""
    def _load(filename: str) -> dict:
        path = FIXTURES_DIR / filename
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return _load


@pytest.fixture
def sample_jd():
    """A sample JD text for quick tests."""
    return """
Software Development Engineer — Acme Corp

About the Role:
We are looking for a Software Development Engineer to join our backend team.

Requirements:
- Strong proficiency in Python
- Experience building RESTful APIs
- Solid understanding of SQL databases (PostgreSQL preferred)
- Strong foundation in data structures and algorithms
- Familiarity with Git version control

Nice to have:
- Familiarity with containerization (Docker)
- Experience with cloud platforms (AWS/GCP)
- Knowledge of CI/CD pipelines

Responsibilities:
- Develop and maintain backend services
- Write clean, testable code
- Collaborate with cross-functional teams
- Participate in code reviews
"""


@pytest.fixture
def sample_resume():
    """A sample resume text for quick tests."""
    return """
PRANAV N
B.Tech Computer Science — University XYZ | GPA: 8.5/10

Skills:
- Languages: Python, JavaScript, C++
- Frameworks: React, Node.js, Flask
- Tools: Git, VS Code, Postman
- Concepts: OOP, Data Structures, Web Development

Projects:
1. Blockchain Voting Platform
   Tech: Solidity, React, Hardhat
   Built a decentralized voting system on Ethereum blockchain.

2. Weather Dashboard
   Tech: Python, Flask, Chart.js
   Real-time weather data visualization dashboard with API integration.

Achievements:
- Smart India Hackathon Finalist
"""
