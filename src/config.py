"""
Centralized configuration for Placement Prep Agent.
Loads from .env locally and st.secrets on Streamlit Cloud.
"""

import os
from pathlib import Path

# Try loading .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Try loading from Streamlit secrets (for Streamlit Cloud deployment)
def _get_secret(key: str, default: str = "") -> str:
    """Get a config value from env vars, Streamlit secrets, or default."""
    # First check environment variables
    val = os.getenv(key)
    if val:
        return val
    # Then try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


# ─── LLM Configuration ───────────────────────────────────────────────
# Manual .env parsing to guarantee we get the latest values without Streamlit caching
_env_vars = {}
try:
    with open(Path(__file__).resolve().parent.parent / ".env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                _env_vars[k.strip()] = v.strip()
except Exception:
    pass

API_KEY: str = _env_vars.get("XAI_API_KEY", _get_secret("XAI_API_KEY"))
MODEL_NAME: str = _env_vars.get("LLM_MODEL", _get_secret("LLM_MODEL", "llama-3.3-70b-versatile"))
if MODEL_NAME == "llama-3.1-70b-versatile":
    MODEL_NAME = "llama-3.3-70b-versatile"
BASE_URL: str = _env_vars.get("LLM_BASE_URL", _get_secret("LLM_BASE_URL", "https://api.x.ai/v1"))

# ─── Mock Mode (for development / testing without API key) ───────────
MOCK_MODE: bool = _get_secret("MOCK_MODE", "false").lower() == "true"

# ─── Database ─────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DB_PATH: Path = PROJECT_ROOT / _get_secret("DB_PATH", "data/sessions.db")
PROBLEMS_PATH: Path = PROJECT_ROOT / "data" / "problems.json"

# ─── Pipeline Defaults ───────────────────────────────────────────────
MAX_PROBLEMS_IN_SET: int = 12
MIN_PROBLEMS_IN_SET: int = 8
MAX_INTERVIEW_QUESTIONS: int = 10
MIN_INTERVIEW_QUESTIONS: int = 6

# ─── LLM Call Settings ───────────────────────────────────────────────
LLM_MAX_RETRIES: int = 3
LLM_RETRY_DELAY: float = 1.0  # seconds, will exponentially backoff
LLM_TEMPERATURE: float = 0.3  # low temp for structured / factual output
LLM_MAX_TOKENS: int = 4096

# ─── Guardrail Settings ──────────────────────────────────────────────
MAX_INPUT_LENGTH: int = 50_000  # characters — reject absurdly long inputs

# ─── Design Constraint (embedded in all LLM system prompts) ──────────
GROUNDING_INSTRUCTION: str = (
    "CRITICAL CONSTRAINT: Only reference information that is explicitly present "
    "in the provided text. Never fabricate, assume, or infer claims about the "
    "student that cannot be directly verified from the resume text. If information "
    "is not present, explicitly state that it is not mentioned."
)
