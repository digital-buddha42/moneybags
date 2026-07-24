# YNAB Weekly Budget Check-in

Pulls your current month's YNAB categories, finds overspent categories and
available money, and asks Claude to write a short natural-language summary.
Runs every Sunday at 7pm (America/Phoenix) via GitHub Actions.

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

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
export $(grep -v '^#' .env | xargs)
python ynab_checkin.py
```

## Model and cost notes

- Defaults to `claude-sonnet-5`. This task is plain summarization — turning
  numbers this script already computed into a short paragraph — not
  multi-step reasoning, so Sonnet is plenty capable and far cheaper than
  Opus. Override with the `ANTHROPIC_MODEL` env var if you want to try
  `claude-haiku-4-5` (even cheaper, still fine for this) or `claude-opus-4-8`
  (no real benefit here, but available).
- Pricing (per million tokens, current as of writing): Sonnet 5 is $3 input /
  $15 output ($2 / $10 introductory through 2026-08-31), Haiku 4.5 is
  $1 / $5, Opus 4.8 is $5 / $25. This script sends a small prompt (a couple
  hundred tokens of category data) and caps the reply at 1024 output tokens,
  so a single run costs a small fraction of a cent regardless of model —
  the model choice mainly matters if you're watching a shared usage/credit
  pool rather than raw dollars.
- Rate limits are a non-issue at this volume — both YNAB (200 requests/hour
  per token) and the Anthropic API's standard tier limits are far beyond one
  request a week.

## What it does

1. `GET /budgets/{budget_id}/months/current` from the YNAB API for the
   current month's category balances.
2. Computes, in Python (not via the model, to avoid any arithmetic
   hallucination): overspent categories (negative balance) sorted by size,
   and categories with money still available (positive balance).
3. Sends those exact numbers to Claude with instructions to write a short,
   plain-English recap — no invented figures.
4. Prints the recap to stdout (visible in the GitHub Actions run log).
