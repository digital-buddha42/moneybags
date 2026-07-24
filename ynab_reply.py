#!/usr/bin/env python3
"""Reply to a comment on a YNAB budget check-in issue.

Triggered by the "Budget Check-in Reply" workflow, which only runs this for
non-bot comments on issues labeled "ynab-checkin" (see that workflow's
`if:` condition) — this script doesn't re-check either.

Pulls fresh YNAB numbers and goal context, feeds them plus the issue's
conversation so far to Claude, and posts the reply as a new comment.

Required environment variables:
    YNAB_TOKEN          YNAB personal access token
    YNAB_BUDGET_ID      YNAB budget id (or "last-used")
    ANTHROPIC_API_KEY   Anthropic API key
    GITHUB_TOKEN        Token for posting the reply comment
    GITHUB_REPOSITORY   Set automatically by GitHub Actions
    GITHUB_EVENT_PATH   Set automatically by GitHub Actions

Optional:
    ANTHROPIC_REPLY_MODEL   Defaults to claude-haiku-4-5-20251001 — this is
                             just constraint-following on numbers already
                             computed, not the more involved weekly summary,
                             so a cheaper model is plenty.
"""

import json
import os
import sys

import anthropic

from github_api import create_issue_comment, list_issue_comments
from goals import fetch_goals_context
from ynab_data import build_data_summary, fetch_current_month, summarize_month

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

REPLY_SYSTEM_PROMPT = (
    "You are a friendly personal-finance assistant continuing a YNAB budget "
    "check-in conversation on a GitHub issue. You already sent an initial "
    "summary; the user is now replying with constraints, questions, or "
    "corrections. You are given the current month's exact YNAB numbers, "
    "freshly recomputed, the user's goals and Rich Life priorities if "
    "available, and the conversation so far. Write a short, warm, "
    "plain-English reply under 150 words that directly addresses what the "
    "user said, using only the numbers given — do not estimate or invent "
    "any. If they've ruled out certain categories, suggest alternatives from "
    "the remaining available categories, and weigh in against their stated "
    "goals where relevant. Plain paragraphs, no markdown headers or bullet "
    "lists."
)


def load_event() -> dict:
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        return json.load(f)


def build_transcript(issue_body: str, comments: list) -> str:
    lines = [f"Initial check-in summary:\n{issue_body}"]
    for c in comments:
        author = "You (assistant)" if c["user"].get("type") == "Bot" else "User"
        lines.append(f"{author}: {c['body']}")
    return "\n\n".join(lines)


def get_claude_reply(data_text: str, goals_context: str, transcript: str, model: str) -> str:
    client = anthropic.Anthropic()

    user_content = f"Current month numbers:\n{data_text}"
    if goals_context:
        user_content += f"\n\nUser's goals and Rich Life priorities:\n{goals_context}"
    user_content += f"\n\nConversation so far:\n{transcript}"

    response = client.messages.create(
        model=model,
        max_tokens=400,
        output_config={"effort": "low"},
        system=REPLY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    return next(block.text for block in response.content if block.type == "text")


def main() -> None:
    ynab_token = os.environ.get("YNAB_TOKEN")
    ynab_budget_id = os.environ.get("YNAB_BUDGET_ID")
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")
    model = os.environ.get("ANTHROPIC_REPLY_MODEL", DEFAULT_MODEL)

    missing = [
        name
        for name, value in [
            ("YNAB_TOKEN", ynab_token),
            ("YNAB_BUDGET_ID", ynab_budget_id),
            ("GITHUB_TOKEN", github_token),
            ("GITHUB_REPOSITORY", github_repo),
        ]
        if not value
    ]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    event = load_event()
    issue = event["issue"]

    month = fetch_current_month(ynab_budget_id, ynab_token)
    summary = summarize_month(month)
    data_text = build_data_summary(summary)
    goals_context = fetch_goals_context()

    comments = list_issue_comments(github_repo, github_token, issue["number"])
    transcript = build_transcript(issue.get("body") or "", comments)

    reply = get_claude_reply(data_text, goals_context, transcript, model)
    create_issue_comment(github_repo, github_token, issue["number"], reply)
    print(reply)


if __name__ == "__main__":
    main()
