/** Copy for the Archive list. Entries themselves are Chinese-native and shown as they are. */
const zh = {
  title: "Archive",
  pageTitle: (n: number) => `Archive 第 ${n} 頁`,
  description: (since: string) => `${since} 以前的每日報告與 2023 年起的 AI news digest 摘要。`,
  intro: (since: string, reports: number, digests: number) => `${since} 以前的每日報告 ${reports} 篇，以及 2023 到 2026 年的 AI news digest ${digests} 期。`,
  monthLabel: (y: string, m: number) => `${y} 年 ${m} 月`,
  reportsHeading: "每日報告",
  reportsCount: (n: number) => `${n} 篇`,
  items: (n: number) => `${n} 則`,
  digestHeading: "AI news digest",
  digestCount: (n: number) => `${n} 期，原文已不保存，只列摘要`,
  paginationLabel: "Archive 分頁",
};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const en: typeof zh = {
  title: "Archive",
  pageTitle: (n) => `Archive, page ${n}`,
  description: (since) => `Daily reports before ${since} and AI news digest summaries from 2023. Entries are in Chinese.`,
  intro: (since, reports, digests) => `${reports} daily reports before ${since}, and ${digests} AI news digest issues from 2023 to 2026. Entries are in Chinese.`,
  monthLabel: (y, m) => `${MONTHS[m - 1] ?? m} ${y}`,
  reportsHeading: "Daily reports",
  reportsCount: (n) => `${n} reports`,
  items: (n) => `${n} items`,
  digestHeading: "AI news digest",
  digestCount: (n) => `${n} issues; originals are not kept, summaries only`,
  paginationLabel: "Archive pagination",
};
export const archiveUI = { zh, en };
