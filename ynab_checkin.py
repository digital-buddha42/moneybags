#!/usr/bin/env python3
"""Weekly YNAB budget check-in.

Pulls the current month's category data from YNAB, works out which
categories are overspent and how much money is still available, then asks
Claude to turn those numbers into a short natural-language summary.

Required environment variables:
    YNAB_TOKEN          YNAB personal access token
    YNAB_BUDGET_ID      YNAB budget id (or "last-used")
    ANTHROPIC_API_KEY   Anthropic API key

Optional:
    ANTHROPIC_MODEL     Defaults to claude-sonnet-5
"""

import os
import sys

import anthropic
import requests

YNAB_API_BASE = "https://api.ynab.com/v1"
DEFAULT_MODEL = "claude-sonnet-5"


def fetch_current_month(budget_id: str, token: str) -> dict:
    resp = requests.get(
        f"{YNAB_API_BASE}/budgets/{budget_id}/months/current",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["month"]


def milliunits_to_dollars(milliunits: int) -> float:
    return milliunits / 1000.0


def summarize_month(month: dict) -> dict:
    categories = [
        c for c in month["categories"] if not c["deleted"] and not c["hidden"]
    ]

    overspent = sorted(
        (
            {
                "group": c["category_group_name"],
                "name": c["name"],
                "overspent_by": -milliunits_to_dollars(c["balance"]),
            }
            for c in categories
            if c["balance"] < 0
        ),
        key=lambda c: c["overspent_by"],
        reverse=True,
    )

    available = sorted(
        (
            {
                "group": c["category_group_name"],
                "name": c["name"],
                "available": milliunits_to_dollars(c["balance"]),
            }
            for c in categories
            if c["balance"] > 0
        ),
        key=lambda c: c["available"],
        reverse=True,
    )

    return {
        "month": month["month"],
        "to_be_budgeted": milliunits_to_dollars(month["to_be_budgeted"]),
        "total_budgeted": milliunits_to_dollars(month["budgeted"]),
        "total_activity": milliunits_to_dollars(month["activity"]),
        "overspent": overspent,
        "available": available,
    }


def build_data_summary(summary: dict) -> str:
    lines = [
        f"To be budgeted (unassigned funds): ${summary['to_be_budgeted']:.2f}",
        f"Total budgeted this month: ${summary['total_budgeted']:.2f}",
        f"Total activity (spending) this month: ${summary['total_activity']:.2f}",
        "",
    ]

    if summary["overspent"]:
        lines.append("Overspent categories:")
        for c in summary["overspent"]:
            lines.append(
                f"- {c['group']}: {c['name']} is ${c['overspent_by']:.2f} over budget"
            )
    else:
        lines.append("No categories are overspent.")

    lines.append("")

    if summary["available"]:
        lines.append("Categories with money still available:")
        for c in summary["available"][:15]:
            lines.append(
                f"- {c['group']}: {c['name']} has ${c['available']:.2f} available"
            )
        remaining = len(summary["available"]) - 15
        if remaining > 0:
            lines.append(f"...and {remaining} more categories with available funds")
    else:
        lines.append("No categories currently have available funds.")

    return "\n".join(lines)


def get_claude_summary(data_text: str, model: str) -> str:
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        output_config={"effort": "low"},
        system=(
            "You are a friendly personal-finance assistant writing a short weekly "
            "budget check-in. You are given exact numbers from a YNAB (You Need A "
            "Budget) snapshot for the current month. Write a concise, warm, "
            "plain-English summary under 200 words: call out any overspent "
            "categories by name and amount, state how much money is still "
            "available (both unassigned and sitting in categories), and give one "
            "or two practical suggestions if anything looks concerning. Use only "
            "the numbers given — do not estimate or invent any. Plain paragraphs, "
            "no markdown headers or bullet lists."
        ),
        messages=[{"role": "user", "content": data_text}],
    )

    return next(block.text for block in response.content if block.type == "text")


def main() -> None:
    ynab_token = os.environ.get("YNAB_TOKEN")
    ynab_budget_id = os.environ.get("YNAB_BUDGET_ID")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

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
    narrative = get_claude_summary(data_text, model)

    print(f"YNAB Weekly Budget Check-in — {summary['month']}")
    print("=" * 50)
    print(narrative)


if __name__ == "__main__":
    main()
