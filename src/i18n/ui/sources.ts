/** Copy for the Sources list. */
const zh = {
  title: "Sources",
  pageTitle: (n: number) => `Sources 第 ${n} 頁`,
  description: "每日快報引用的新聞，依日期與來源分組。",
  introBefore: "每日快報引用的新聞，依日期與",
  introLink: "來源",
  introAfter: "分組。",
  stats: (since: string, days: number, items: number) => `${since} 起共 ${days} 天、${items} 則`,
  range: (r: string) => `，這頁是 ${r}`,
  end: "。",
  dayCount: (items: number, sources: number) => `${items} 則 · ${sources} 個來源`,
  viewReport: "看快報 →",
  paginationLabel: "Sources 分頁",
  empty: "還沒有收錄任何新聞，第一份每日快報產生後會出現在這裡。",
};
const en: typeof zh = {
  title: "Sources",
  pageTitle: (n) => `Sources, page ${n}`,
  description: "News cited by the daily digests, grouped by date and source.",
  introBefore: "News cited by the daily digests, grouped by date and ",
  introLink: "source",
  introAfter: ".",
  stats: (since, days, items) => `${days} days and ${items} items since ${since}`,
  range: (r) => `; this page covers ${r}`,
  end: ".",
  dayCount: (items, sources) => `${items} items · ${sources} sources`,
  viewReport: "View digest →",
  paginationLabel: "Sources pagination",
  empty: "No news has been collected yet. It will show up here once the first daily digest is generated.",
};
export const sourcesUI = { zh, en };
