# moneybags MCP server

A remote MCP server on Cloudflare Workers that exposes live YNAB budget data
and goal context as tools, so you can ask Claude (including the Claude
mobile app) things like "can I afford this?" any time — not just on the
weekly cadence.

## Tools

- `get_budget_summary` — this month's unassigned funds, overspent
  categories, and categories with money available.
- `check_affordability(amount, description?)` — same data, framed around
  whether a specific purchase fits. Read-only; never moves money.
- `get_goals` — goal/Rich-Life context from the
  [`goals-tracker`](https://github.com/digital-buddha42/goals-tracker) repo.

The server only returns data — the reasoning about whether something's a
good idea happens in Claude's own turn in your conversation, the same as
any other tool call. That also means there's no extra Anthropic API cost
per query: it's covered by your existing Claude usage, not a second
API call the server makes on your behalf.

## Deploy

Requires a (free) [Cloudflare account](https://dash.cloudflare.com/sign-up)
and Node 18+.

```bash
cd mcp-server
npm install

# Log in to your Cloudflare account (opens a browser)
npx wrangler login

# Set secrets (never commit these — see .dev.vars below for local testing)
npx wrangler secret put YNAB_TOKEN
npx wrangler secret put YNAB_BUDGET_ID
npx wrangler secret put MCP_AUTH_TOKEN   # a long random string, e.g. `openssl rand -hex 32` — this is what protects your endpoint, treat it like a password

npx wrangler deploy
```

Deploy prints your server's URL, something like
`https://moneybags-mcp.<your-subdomain>.workers.dev`. The MCP endpoint is
that URL plus `/mcp`.

## Add it to Claude

In the Claude app: **Settings → Connectors → Add custom connector**.

- **URL**: `https://moneybags-mcp.<your-subdomain>.workers.dev/mcp`
- **Authorization header**: `Bearer <the MCP_AUTH_TOKEN you set above>`

Once added, any conversation (including on your phone) can ask things like
"can I afford a $150 guitar pedal?" and Claude will call `check_affordability`
directly.

## Local development

```bash
cp .dev.vars.example .dev.vars   # fill in real or test values
npm run dev
```

`wrangler dev` runs the server locally at `http://localhost:8787/mcp`.
`.dev.vars` is gitignored — never commit real tokens to it.

## Cost

Cloudflare Workers' free tier (100,000 requests/day) covers personal use
many times over, so this is effectively free to run. See "Tools" above for
why there's no added Anthropic API cost either.
