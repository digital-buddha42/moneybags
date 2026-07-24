"""Fetch financial-goal context from the public goals-tracker repo.

goals-tracker (github.com/digital-buddha42/goals-tracker) keeps the
user's current goals and "Rich Life" priorities in its CLAUDE.md. The repo
is public, so this is a plain, unauthenticated read of the raw file.
"""

import re

import requests

GOALS_CLAUDE_MD_URL = (
    "https://raw.githubusercontent.com/digital-buddha42/goals-tracker/main/CLAUDE.md"
)
SECTION_MARKERS = ("goal", "rich life")


def fetch_goals_context() -> str:
    """Return the goals/Rich-Life sections of CLAUDE.md, or "" if unavailable."""
    try:
        resp = requests.get(GOALS_CLAUDE_MD_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    sections = re.split(r"(?m)^## ", resp.text)[1:]
    matched = [
        "## " + s.rstrip()
        for s in sections
        if any(marker in s.split("\n", 1)[0].lower() for marker in SECTION_MARKERS)
    ]
    return "\n\n".join(matched).strip()
