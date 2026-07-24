const GOALS_CLAUDE_MD_URL =
  "https://raw.githubusercontent.com/digital-buddha42/goals-tracker/main/CLAUDE.md";
const SECTION_MARKERS = ["goal", "rich life"];

export async function fetchGoalsContext(): Promise<string> {
  try {
    const resp = await fetch(GOALS_CLAUDE_MD_URL);
    if (!resp.ok) return "";
    const text = await resp.text();

    const sections = text.split(/^## /m).slice(1);
    const matched = sections
      .filter((s) => {
        const heading = s.split("\n", 1)[0].toLowerCase();
        return SECTION_MARKERS.some((marker) => heading.includes(marker));
      })
      .map((s) => "## " + s.trimEnd());

    return matched.join("\n\n").trim();
  } catch {
    return "";
  }
}
