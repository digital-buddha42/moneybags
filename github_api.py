"""Minimal GitHub REST API helpers for issue-based interaction."""

import requests

GITHUB_API_BASE = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def create_issue(repo: str, token: str, title: str, body: str, labels: list) -> int:
    resp = requests.post(
        f"{GITHUB_API_BASE}/repos/{repo}/issues",
        headers=_headers(token),
        json={"title": title, "body": body, "labels": labels},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["number"]


def list_issue_comments(repo: str, token: str, issue_number: int) -> list:
    resp = requests.get(
        f"{GITHUB_API_BASE}/repos/{repo}/issues/{issue_number}/comments",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def create_issue_comment(repo: str, token: str, issue_number: int, body: str) -> None:
    resp = requests.post(
        f"{GITHUB_API_BASE}/repos/{repo}/issues/{issue_number}/comments",
        headers=_headers(token),
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()
