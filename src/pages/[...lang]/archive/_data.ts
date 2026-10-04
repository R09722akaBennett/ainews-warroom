import { SITE_SINCE } from "@consts";
import legacyData from "../../../data/legacy.json";
import reportsData from "../../../data/reports.json";

export type Entry = { kind: "report" | "digest"; date: string; item: any };

export const PER_PAGE = 50;
export const oldReports = (reportsData as any[]).filter((r) => r.date < SITE_SINCE).sort((a, b) => b.date.localeCompare(a.date));
export const digests = (legacyData as any[]).slice().sort((a, b) => b.date.localeCompare(a.date));

// Reports come first, then the digests, so each kind stays contiguous and a
// page boundary splits at most one month of one kind.
export const entries: Entry[] = [
  ...oldReports.map((item) => ({ kind: "report" as const, date: item.date, item })),
  ...digests.map((item) => ({ kind: "digest" as const, date: item.date, item })),
];
