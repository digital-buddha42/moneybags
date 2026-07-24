import { createMcpHandler } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

import { fetchGoalsContext } from "./goals";
import { buildAffordabilityText, buildDataSummary, fetchCurrentMonth, summarizeMonth } from "./ynab";

export interface Env {
  YNAB_TOKEN: string;
  YNAB_BUDGET_ID: string;
  MCP_AUTH_TOKEN: string;
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

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const expected = `Bearer ${env.MCP_AUTH_TOKEN}`;
    const provided = request.headers.get("Authorization");
    if (!env.MCP_AUTH_TOKEN || provided !== expected) {
      return new Response("Unauthorized", { status: 401 });
    }

    const server = createServer(env);
    return createMcpHandler(server)(request, env, ctx);
  }
};
