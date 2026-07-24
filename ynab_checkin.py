#!/usr/bin/env python3
"""Weekly YNAB budget check-in.

Pulls the current month's category data from YNAB, works out which
categories are overspent and how much money is still available, and asks
Claude to turn those numbers (plus the user's goals, if available) into a
short natural-language summary. Opens a GitHub issue with the summary so
the user can reply with constraints and get a follow-up (see
ynab_reply.py).

Required environment variables:
    YNAB_TOKEN          YNAB personal access token
    YNAB_BUDGET_ID      YNAB budget id (or "last-used")
    ANTHROPIC_API_KEY   Anthropic API key

Optional:
    ANTHROPIC_MODEL     Defaults to claude-sonnet-5
    GITHUB_TOKEN        If set (with GITHUB_REPOSITORY), opens a GitHub
                         issue with the summary instead of just printing it
"""

import os
import sys

import anthropic

from github_api import create_issue
from goals import fetch_goals_context
from ynab_data import build_data_summary, fetch_current_month, summarize_month

DEFAULT_MODEL = "claude-sonnet-5"
ISSUE_LABEL = "ynab-checkin"


def get_claude_summary(data_text: str, goals_context: str, model: str) -> str:
    client = anthropic.Anthropic()

    user_content = data_text
    if goals_context:
        user_content += (
            "\n\nFor context, here are the user's current goals and Rich Life "
            "priorities (from a separate personal tracker):\n" + goals_context
        )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        output_config={"effort": "low"},
        system=(
            "You are a friendly personal-finance assistant writing a short weekly "
            "budget check-in. You are given exact numbers from a YNAB (You Need A "
            "Budget) snapshot for the current month, and possibly the user's "
            "personal goals and Rich Life priorities from a separate tracker. "
            "Write a concise, warm, plain-English summary under 200 words: call "
            "out any overspent categories by name and amount, state how much "
            "money is still available (both unassigned and sitting in "
            "categories), and give one or two practical suggestions if anything "
            "looks concerning. If goals context is given, weigh it in — protect "
            "Rich Life pillars, and flag anything working against a stated goal "
            "or money milestone. Use only the numbers given — do not estimate or "
            "invent any. Plain paragraphs, no markdown headers or bullet lists."
        ),
        messages=[{"role": "user", "content": user_content}],
    )

    return next(block.text for block in response.content if block.type == "text")


def main() -> None:
    ynab_token = os.environ.get("YNAB_TOKEN")
    ynab_budget_id = os.environ.get("YNAB_BUDGET_ID")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")

    missing = [
        name
        for name, value in [("YNAB_TOKEN", ynab_token), ("YNAB_BUDGET_ID", ynab_budget_id)]
        if not value
    ]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    month = fetch_current_month(ynab_budget_id, ynab_token)
    summary = summarize_month(month)
    data_text = build_data_summary(summary)
    goals_context = fetch_goals_context()
    narrative = get_claude_summary(data_text, goals_context, model)

    print(f"YNAB Weekly Budget Check-in — {summary['month']}")
    print("=" * 50)
    print(narrative)

    if github_token and github_repo:
        issue_body = (
            narrative
            + "\n\nReply on this issue with any constraints (e.g. \"can't touch "
            "Auto Insurance, it's due soon\") and I'll factor that into an "
            "updated suggestion."
        )
        issue_number = create_issue(
            github_repo,
            github_token,
            title=f"Budget check-in — {summary['month']}",
            body=issue_body,
            labels=[ISSUE_LABEL],
        )
        print(f"\nOpened issue #{issue_number}")
    else:
        print("\nGITHUB_TOKEN/GITHUB_REPOSITORY not set — skipping issue creation.")


if __name__ == "__main__":
    main()
