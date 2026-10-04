import { SITE_SINCE } from "@consts";
import allReports from "../../data/reports.json";

export const PER_PAGE = 30;
export const reports = (allReports as any[])
  .filter((r) => r.date >= SITE_SINCE)
  .sort((a, b) => b.date.localeCompare(a.date));
