import { SITE_SINCE } from "@consts";
import reportsData from "../../../data/reports.json";

type SourceItem = { url: string; title: string; source: string };
type SourceGroup = { name: string; items: SourceItem[] };
type DayData = { groups: SourceGroup[]; total: number };

export const DAYS_PER_PAGE = 7;

const reports = (reportsData as any[]).filter((r) => r.date >= SITE_SINCE);

export const byDate: Record<string, DayData> = {};
for (const report of reports) {
  const bySource: Record<string, SourceItem[]> = {};
  for (const item of (report.newsItems || []) as SourceItem[]) {
    if (!item?.url) continue;
    (bySource[item.source || "Other"] ||= []).push(item);
  }
  const groups = Object.entries(bySource)
    .map(([name, items]) => ({ name, items }))
    .sort((a, b) => b.items.length - a.items.length || a.name.localeCompare(b.name));
  byDate[report.date] = { groups, total: groups.reduce((sum, g) => sum + g.items.length, 0) };
}

export const dates = Object.keys(byDate).sort().reverse();
export const totalItems = dates.reduce((sum, d) => sum + byDate[d].total, 0);
