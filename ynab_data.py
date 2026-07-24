"""Shared YNAB API and budget-summary helpers."""

import requests

YNAB_API_BASE = "https://api.ynab.com/v1"


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
