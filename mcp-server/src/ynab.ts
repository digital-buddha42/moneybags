const YNAB_API_BASE = "https://api.ynab.com/v1";

interface RawCategory {
  deleted: boolean;
  hidden: boolean;
  balance: number;
  name: string;
  category_group_name: string;
}

interface RawMonth {
  month: string;
  to_be_budgeted: number;
  budgeted: number;
  activity: number;
  categories: RawCategory[];
}

export interface CategoryAmount {
  group: string;
  name: string;
  amount: number;
}

export interface MonthSummary {
  month: string;
  toBeBudgeted: number;
  totalBudgeted: number;
  totalActivity: number;
  overspent: CategoryAmount[];
  available: CategoryAmount[];
}

function milliunitsToDollars(milliunits: number): number {
  return milliunits / 1000;
}

export async function fetchCurrentMonth(budgetId: string, token: string): Promise<RawMonth> {
  const resp = await fetch(`${YNAB_API_BASE}/budgets/${budgetId}/months/current`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!resp.ok) {
    throw new Error(`YNAB API error: ${resp.status} ${await resp.text()}`);
  }
  const json = (await resp.json()) as { data: { month: RawMonth } };
  return json.data.month;
}

export function summarizeMonth(month: RawMonth): MonthSummary {
  const categories = month.categories.filter(
    (c) => !c.deleted && !c.hidden && c.category_group_name !== "Internal Master Category"
  );

  const overspent = categories
    .filter((c) => c.balance < 0)
    .map((c) => ({
      group: c.category_group_name,
      name: c.name,
      amount: -milliunitsToDollars(c.balance)
    }))
    .sort((a, b) => b.amount - a.amount);

  const available = categories
    .filter((c) => c.balance > 0)
    .map((c) => ({
      group: c.category_group_name,
      name: c.name,
      amount: milliunitsToDollars(c.balance)
    }))
    .sort((a, b) => b.amount - a.amount);

  return {
    month: month.month,
    toBeBudgeted: milliunitsToDollars(month.to_be_budgeted),
    totalBudgeted: milliunitsToDollars(month.budgeted),
    totalActivity: milliunitsToDollars(month.activity),
    overspent,
    available
  };
}

export function buildDataSummary(summary: MonthSummary): string {
  const lines: string[] = [
    `To be budgeted (unassigned funds): $${summary.toBeBudgeted.toFixed(2)}`,
    `Total budgeted this month: $${summary.totalBudgeted.toFixed(2)}`,
    `Total activity (spending) this month: $${summary.totalActivity.toFixed(2)}`,
    ""
  ];

  if (summary.overspent.length) {
    lines.push("Overspent categories:");
    for (const c of summary.overspent) {
      lines.push(`- ${c.group}: ${c.name} is $${c.amount.toFixed(2)} over budget`);
    }
  } else {
    lines.push("No categories are overspent.");
  }

  lines.push("");

  if (summary.available.length) {
    lines.push("Categories with money still available:");
    for (const c of summary.available.slice(0, 15)) {
      lines.push(`- ${c.group}: ${c.name} has $${c.amount.toFixed(2)} available`);
    }
    const remaining = summary.available.length - 15;
    if (remaining > 0) {
      lines.push(`...and ${remaining} more categories with available funds`);
    }
  } else {
    lines.push("No categories currently have available funds.");
  }

  return lines.join("\n");
}

export function buildAffordabilityText(
  summary: MonthSummary,
  amount: number,
  description?: string
): string {
  const label = description ? `"${description}" ($${amount.toFixed(2)})` : `a $${amount.toFixed(2)} purchase`;
  const lines: string[] = [`Checking affordability for ${label}.`, ""];

  lines.push(`Unassigned funds (to be budgeted): $${summary.toBeBudgeted.toFixed(2)}.`);
  if (summary.toBeBudgeted >= amount) {
    lines.push("This fits entirely within unassigned funds.");
  } else {
    const shortfall = amount - summary.toBeBudgeted;
    lines.push(`Unassigned funds alone fall short by $${shortfall.toFixed(2)}.`);
  }
  lines.push("");

  if (summary.overspent.length) {
    lines.push("Overspent categories (already over budget, don't pull from these):");
    for (const c of summary.overspent) {
      lines.push(`- ${c.group}: ${c.name} is $${c.amount.toFixed(2)} over budget`);
    }
    lines.push("");
  }

  if (summary.available.length) {
    lines.push("Categories with money available that could be reallocated to cover a shortfall:");
    for (const c of summary.available) {
      lines.push(`- ${c.group}: ${c.name} has $${c.amount.toFixed(2)} available`);
    }
  } else {
    lines.push("No categories currently have available funds to reallocate.");
  }

  return lines.join("\n");
}
