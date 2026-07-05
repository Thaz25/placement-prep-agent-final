"""
Guardrails — Prompt injection detection for JD and resume inputs.
Uses heuristic/rule-based detection for speed and zero API cost.
"""

import re
import base64
import logging
from dataclasses import dataclass, field

from src import config

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    is_safe: bool
    flags: list[str] = field(default_factory=list)
    sanitized_text: str = ""


# ─── Injection Patterns ──────────────────────────────────────────────
# Each tuple: (pattern_regex, flag_description)
INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Direct instruction override
    (r"ignore\s+(all\s+)?previous\s+instructions", "Direct instruction override: 'ignore previous instructions'"),
    (r"disregard\s+(all\s+)?(above|previous|prior)", "Direct instruction override: 'disregard above'"),
    (r"forget\s+(all\s+)?(your|the)\s+instructions", "Instruction override: 'forget your instructions'"),
    (r"you\s+are\s+now\s+", "Role manipulation: 'you are now...'"),
    (r"new\s+instructions?\s*:", "Instruction injection: 'new instructions:'"),
    (r"override\s+(previous|system|all)\s+", "Instruction override attempt"),

    # System prompt extraction
    (r"(repeat|show|display|output|reveal|print)\s+(your|the)\s+(system\s+)?prompt", "System prompt extraction attempt"),
    (r"what\s+are\s+your\s+(initial\s+)?instructions", "System prompt extraction attempt"),
    (r"(show|tell)\s+me\s+your\s+(system\s+)?(message|prompt|instructions)", "System prompt extraction attempt"),

    # Role manipulation / jailbreak
    (r"\bDAN\b.*mode", "Jailbreak: DAN mode reference"),
    (r"jailbreak", "Jailbreak keyword detected"),
    (r"developer\s+mode\s+(enabled|activated|on)", "Jailbreak: developer mode"),
    (r"(act|behave|respond)\s+as\s+(if\s+)?(you\s+are\s+)?(an?\s+)?(ai|assistant|expert|hacker|dan|bot|system)", "Suspicious role reassignment"),

    # Delimiter injection
    (r"<\/?s>", "Delimiter injection: message boundary tag"),
    (r"\[/?INST\]", "Delimiter injection: instruction tag"),
    (r"<<\s*SYS\s*>>", "Delimiter injection: system tag"),
    (r"```system", "Delimiter injection: system code block"),

    # Prompt leaking via encoding
    (r"base64\s*:\s*[A-Za-z0-9+/]{20,}", "Encoded payload: base64 reference"),
    (r"hex\s*:\s*[0-9a-fA-F]{20,}", "Encoded payload: hex reference"),
]

# Known base64-encoded injection prefixes
KNOWN_B64_INJECTIONS = [
    "aWdub3JlIHByZXZpb3Vz",  # "ignore previous"
    "ZGlzcmVnYXJkIGFib3Zl",  # "disregard above"
    "Zm9yZ2V0IHlvdXIgaW5z",  # "forget your ins..."
]


def _check_patterns(text: str) -> list[str]:
    """Check text against all injection patterns. Returns list of flag descriptions."""
    flags = []
    text_lower = text.lower()

    for pattern, description in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            flags.append(description)
            logger.warning(f"[GUARDRAIL] Flag: {description}")

    return flags


def _check_base64_payloads(text: str) -> list[str]:
    """Check for known base64-encoded injection attempts."""
    flags = []
    for b64_prefix in KNOWN_B64_INJECTIONS:
        if b64_prefix in text:
            flags.append(f"Known base64-encoded injection payload detected")
            break

    # Also check for suspicious base64 blocks
    b64_pattern = re.findall(r'[A-Za-z0-9+/]{40,}={0,2}', text)
    for block in b64_pattern:
        try:
            decoded = base64.b64decode(block).decode('utf-8', errors='ignore').lower()
            if any(kw in decoded for kw in ['ignore', 'disregard', 'forget', 'system prompt', 'jailbreak']):
                flags.append(f"Decoded base64 block contains injection keywords")
                break
        except Exception:
            pass

    return flags


def _check_unicode_abuse(text: str) -> list[str]:
    """Check for excessive Unicode control characters or zero-width characters."""
    flags = []
    # Zero-width characters
    zw_chars = ['\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff']
    zw_count = sum(text.count(c) for c in zw_chars)
    if zw_count > 5:
        flags.append(f"Excessive zero-width Unicode characters detected ({zw_count} found)")

    # Control characters (excluding normal whitespace)
    control_count = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
    if control_count > 3:
        flags.append(f"Suspicious control characters detected ({control_count} found)")

    return flags


def _sanitize_text(text: str) -> str:
    """Remove control characters and zero-width chars, preserving normal whitespace."""
    # Remove zero-width characters
    for c in ['\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff']:
        text = text.replace(c, '')
    # Remove control characters except \n, \r, \t
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')
    return text.strip()


def check_guardrails(text: str, input_type: str = "input") -> GuardrailResult:
    """
    Run all guardrail checks on the provided text.

    Args:
        text: The JD or resume text to check.
        input_type: "jd" or "resume" — used for logging.

    Returns:
        GuardrailResult with is_safe, flags, and sanitized_text.
    """
    if not text or not text.strip():
        return GuardrailResult(
            is_safe=False,
            flags=[f"Empty {input_type} text provided"],
            sanitized_text="",
        )

    # Length check
    if len(text) > config.MAX_INPUT_LENGTH:
        return GuardrailResult(
            is_safe=False,
            flags=[f"{input_type.upper()} text exceeds maximum length ({len(text):,} > {config.MAX_INPUT_LENGTH:,} chars)"],
            sanitized_text="",
        )

    all_flags = []

    # Run all checks
    all_flags.extend(_check_patterns(text))
    all_flags.extend(_check_base64_payloads(text))
    all_flags.extend(_check_unicode_abuse(text))

    # Sanitize
    sanitized = _sanitize_text(text)

    is_safe = len(all_flags) == 0

    if not is_safe:
        logger.warning(
            f"[GUARDRAIL] {input_type.upper()} flagged with {len(all_flags)} issue(s): "
            + "; ".join(all_flags)
        )

    return GuardrailResult(
        is_safe=is_safe,
        flags=all_flags,
        sanitized_text=sanitized,
    )
