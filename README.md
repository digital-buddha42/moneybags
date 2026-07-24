# YNAB Weekly Budget Check-in

Pulls your current month's YNAB categories, finds overspent categories and
available money, and asks Claude to write a short natural-language summary.
Runs every Sunday at 7pm (America/Phoenix) via GitHub Actions, posted as a
GitHub issue you can reply to (see "Interactive replies" below).

## Setup

### 1. Get your credentials

- **YNAB token**: YNAB web app → **Account Settings → Developer Settings → New Token**.
- **YNAB budget id**: open your budget in the YNAB web app; the id is the
  UUID in the URL (`app.ynab.com/<budget-id>/budget`). You can also use the
  literal string `last-used`.
- **Anthropic API key**: [console.claude.com](https://console.claude.com) → **API Keys**.

Never paste these into chat or commit them to the repo — add them as
repository secrets (next step) instead.

### 2. Create the repo and push these files

```bash
git init
git add .
git commit -m "Add weekly YNAB budget check-in script"
git branch -M main
git remote add origin <your-new-repo-url>
git push -u origin main
```

### 3. Add repository secrets

In the new repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add:

- `YNAB_TOKEN`
- `YNAB_BUDGET_ID`
- `ANTHROPIC_API_KEY`

### 4. That's it

`.github/workflows/weekly-checkin.yml` runs the script every Sunday at 7pm
Phoenix time (`0 2 * * 1` UTC — Arizona has no DST, so this cron line stays
correct year-round). You can also trigger it manually from the **Actions**
tab (**Run workflow**) to test it immediately, and check the run's logs for
the printed summary.

## Interactive replies

Each weekly run opens a GitHub issue (labeled `ynab-checkin`) with the
summary instead of just logging it. Reply on that issue with any
constraint — "can't touch Auto Insurance, it's due soon" — and
`.github/workflows/budget-checkin-reply.yml` fires on your comment,
re-fetches fresh YNAB numbers, and posts a follow-up that accounts for
what you said. It ignores comments from the bot itself (no reply loops)
and only runs on issues carrying the `ynab-checkin` label, via the
workflow's `if:` condition — so it won't fire on unrelated issues.

Both the weekly summary and the replies also pull goal/Rich-Life context
from the public
[`digital-buddha42/goals-tracker`](https://github.com/digital-buddha42/goals-tracker)
repo's `CLAUDE.md` (plain unauthenticated fetch, no token needed) and
factor it into the advice.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
export $(grep -v '^#' .env | xargs)
python ynab_checkin.py
```

## Model and cost notes

- The weekly summary (`ynab_checkin.py`) defaults to `claude-sonnet-5`.
  Replies (`ynab_reply.py`) default to `claude-haiku-4-5-20251001` — a
  reply is just "interpret a constraint and restate the numbers," not the
  more involved weekly write-up, so the cheaper model is plenty. Override
  with `ANTHROPIC_MODEL` (weekly) or `ANTHROPIC_REPLY_MODEL` (replies) if
  you want something else.
- Pricing (per million tokens, current as of writing): Sonnet 5 is $3 input /
  $15 output ($2 / $10 introductory through 2026-08-31), Haiku 4.5 is
  $1 / $5. Each call sends well under 2,000 tokens of input and is capped
  at 1024 (weekly) or 400 (reply) output tokens, so every run — weekly
  summary or reply — costs on the order of a fraction of a cent. Even a
  chatty week with many replies stays well under a dollar.
- Rate limits are a non-issue at this volume — both YNAB (200 requests/hour
  per token) and the Anthropic API's standard tier limits are far beyond
  this usage.

## What it does

1. `GET /budgets/{budget_id}/months/current` from the YNAB API for the
   current month's category balances.
2. Computes, in Python (not via the model, to avoid any arithmetic
   hallucination): overspent categories (negative balance) sorted by size,
   and categories with money still available (positive balance).
3. Fetches goal/Rich-Life context from `goals-tracker`'s `CLAUDE.md`, if
   reachable.
4. Sends those exact numbers (plus goal context, if any) to Claude with
   instructions to write a short, plain-English recap — no invented
   figures.
5. Prints the recap to stdout and opens it as a GitHub issue labeled
   `ynab-checkin`. Replies on that issue re-run steps 1-4 with fresh data
   and post a follow-up (`ynab_reply.py`, triggered by
   `budget-checkin-reply.yml`).
