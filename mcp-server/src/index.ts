import { createMcpHandler } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { OAuthProvider, type OAuthHelpers } from "@cloudflare/workers-oauth-provider";
import { z } from "zod";

import { fetchGoalsContext } from "./goals";
import { buildAffordabilityText, buildDataSummary, fetchCurrentMonth, summarizeMonth } from "./ynab";

export interface Env {
  YNAB_TOKEN: string;
  YNAB_BUDGET_ID: string;
  MCP_AUTH_TOKEN: string;
  OAUTH_PROVIDER: OAuthHelpers;
  OAUTH_KV: KVNamespace;
}

function createServer(env: Env): McpServer {
  const server = new McpServer({ name: "moneybags", version: "1.0.0" });

  server.registerTool(
    "get_budget_summary",
    {
      description:
        "Get this month's YNAB budget summary: unassigned funds, overspent categories, and categories with money still available.",
      inputSchema: {}
    },
    async () => {
      const month = await fetchCurrentMonth(env.YNAB_BUDGET_ID, env.YNAB_TOKEN);
      const summary = summarizeMonth(month);
      return { content: [{ type: "text", text: buildDataSummary(summary) }] };
    }
  );

  server.registerTool(
    "check_affordability",
    {
      description:
        "Check whether a purchase fits in the current month's YNAB budget. Returns unassigned funds, overspent categories to avoid pulling from, and categories with money available that could realistically cover the cost. Does not move any money — read-only.",
      inputSchema: {
        amount: z.number().describe("Cost of the item in dollars"),
        description: z.string().optional().describe("What the item is, for context")
      }
    },
    async ({ amount, description }) => {
      const month = await fetchCurrentMonth(env.YNAB_BUDGET_ID, env.YNAB_TOKEN);
      const summary = summarizeMonth(month);
      return { content: [{ type: "text", text: buildAffordabilityText(summary, amount, description) }] };
    }
  );

  server.registerTool(
    "get_goals",
    {
      description:
        "Get the user's current goals and Rich Life priorities from their personal goals tracker, to weigh against spending decisions.",
      inputSchema: {}
    },
    async () => {
      const goals = await fetchGoalsContext();
      return { content: [{ type: "text", text: goals || "No goals context available." }] };
    }
  );

  return server;
}

const apiHandler = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const server = createServer(env);
    return createMcpHandler(server)(request, env, ctx);
  }
};

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function loginPage(query: string, error?: string): string {
  const errorHtml = error
    ? `<p style="color:#b91c1c;margin:0 0 12px;font-size:14px;">${escapeHtml(error)}</p>`
    : "";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Connect to your budget</title>
</head>
<body style="font-family: system-ui, sans-serif; display:grid; place-items:center; min-height:100vh; margin:0; background:#f8fafc;">
  <form method="POST" action="/authorize${escapeHtml(query)}"
        style="background:#fff; padding:24px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); width:100%; max-width:320px;">
    <h1 style="font-size:18px; margin:0 0 16px;">Connect to your budget</h1>
    ${errorHtml}
    <label style="display:block; font-size:14px; margin-bottom:4px;">Password</label>
    <input name="password" type="password" required autocomplete="current-password"
           style="width:100%; box-sizing:border-box; padding:8px; border:1px solid #cbd5e1; border-radius:4px; margin-bottom:12px;" />
    <button type="submit"
            style="width:100%; padding:8px; background:#111827; color:#fff; border:none; border-radius:4px; font-weight:600;">
      Continue
    </button>
  </form>
</body>
</html>`;
}

const defaultHandler = {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname !== "/authorize") {
      return new Response("Not found", { status: 404 });
    }

    const oauthReqInfo = await env.OAUTH_PROVIDER.parseAuthRequest(request);

    if (request.method === "GET") {
      return new Response(loginPage(url.search), {
        headers: { "content-type": "text/html; charset=utf-8" }
      });
    }

    if (request.method === "POST") {
      const form = await request.formData();
      const password = String(form.get("password") || "");

      if (!env.MCP_AUTH_TOKEN || password !== env.MCP_AUTH_TOKEN) {
        return new Response(loginPage(url.search, "Wrong password."), {
          status: 401,
          headers: { "content-type": "text/html; charset=utf-8" }
        });
      }

      const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
        request: oauthReqInfo,
        userId: "owner",
        metadata: {},
        scope: oauthReqInfo.scope,
        props: {}
      });

      return Response.redirect(redirectTo, 302);
    }

    return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET, POST" } });
  }
};

export default new OAuthProvider({
  apiRoute: "/mcp",
  apiHandler,
  defaultHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register"
});
