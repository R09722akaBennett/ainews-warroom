/** Copy for the Reading list and article pages. */
const zh = {
  title: "Reading",
  heading: "深讀",
  pageTitle: (n: number) => `第 ${n} 頁`,
  description: "ByteByteGo、Daily Dose of DS、Berkeley RDI 與 ExplainThis 四份電子報的分段重點整理。",
  intro: (names: string[], count: number, days: number, total: number) =>
    `${names.join("、")} 這 ${count} 份電子報的分段重點，最近 ${days} 天共 ${total} 篇`,
  introSource: (name: string, n: number) => `，其中 ${name} ${n} 篇`,
  introEnd: "。",
  tabsLabel: "依來源",
  all: "全部",
  original: "原文 ↗",
  paginationLabel: "Reading 分頁",
  back: "← 回到 Reading",
  readOriginal: "閱讀原文 ↗",
  toc: "目錄",
  sectionCount: (n: number) => `${n} 段`,
  noSections: "這篇還沒有分段整理，請直接閱讀原文。",
  // Source cadence by source key; cadenceOf() falls back to the data's own text for unknown keys.
  cadence: {
    "gmail:bytebytego": "每週約 5 封",
    "gmail:daily_dose_of_ds": "每週 1 到 2 封",
    "gmail:berkeley_rdi": "每週三",
    "gmail:explainthis": "隔週日",
    "gmail:latent_space": "不定期，每週 0 到 2 篇",
    "gmail:the_batch": "每週三",
    "gmail:aihao": "不定期",
    "gmail:datatalks": "每週",
  } as Record<string, string>,
};
const en: typeof zh = {
  title: "Reading",
  heading: "Deep reads",
  pageTitle: (n) => `page ${n}`,
  description: "Section-by-section takeaways from newsletters including ByteByteGo, Daily Dose of DS, Berkeley RDI and ExplainThis.",
  intro: (names, count, days, total) => `Section-by-section takeaways from ${count} newsletters (${names.join(", ")}); ${total} articles in the last ${days} days`,
  introSource: (name, n) => `, ${n} of them from ${name}`,
  introEnd: ".",
  tabsLabel: "By source",
  all: "All",
  original: "Original ↗",
  paginationLabel: "Reading pagination",
  back: "← Back to Reading",
  readOriginal: "Read the original ↗",
  toc: "Contents",
  sectionCount: (n) => `${n} sections`,
  noSections: "This article has no section summary yet; please read the original.",
  cadence: {
    "gmail:bytebytego": "About 5 emails a week",
    "gmail:daily_dose_of_ds": "1 to 2 emails a week",
    "gmail:berkeley_rdi": "Wednesdays",
    "gmail:explainthis": "Every other Sunday",
    "gmail:latent_space": "Irregular, 0 to 2 posts a week",
    "gmail:the_batch": "Wednesdays",
    "gmail:aihao": "Irregular",
    "gmail:datatalks": "Weekly",
  },
};
export const readingUI = { zh, en };

/** The cadence in the page language, falling back to the data's own text. */
export function cadenceOf(lang: "zh" | "en", key: string, fallback: string): string {
  return readingUI[lang].cadence[key] ?? fallback;
}
