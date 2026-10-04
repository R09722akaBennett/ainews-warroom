/** Copy for the Insights (trends) page. */
const zh = {
  title: "Insights",
  description: "每週、每月與每季的 AI 產業趨勢整理。",
  intro: (n: number) => `每週、每月與每季的 AI 產業趨勢整理，共 ${n} 份。`,
  weekly: { label: "週報", badge: "週" },
  monthly: { label: "月報", badge: "月" },
  quarterly: { label: "季報", badge: "季" },
  tokens: (i: string, o: string) => `輸入 ${i} · 輸出 ${o} tokens`,
  empty: (label: string) => `還沒有${label}，第一份產生後會出現在這裡。`,
};
const en: typeof zh = {
  title: "Insights",
  description: "Weekly, monthly and quarterly roundups of AI industry trends.",
  intro: (n) => `Weekly, monthly and quarterly roundups of AI industry trends, ${n} in total.`,
  weekly: { label: "Weekly", badge: "W" },
  monthly: { label: "Monthly", badge: "M" },
  quarterly: { label: "Quarterly", badge: "Q" },
  tokens: (i, o) => `in ${i} · out ${o} tokens`,
  empty: (label) => `No ${label.toLowerCase()} report yet; the first one will appear here once it is generated.`,
};
export const trendsUI = { zh, en };
