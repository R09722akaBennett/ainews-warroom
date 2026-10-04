/** Copy for the About page; the notes describe the pipelines and follow the cron table in README. */
const zh = {
  title: "About",
  description: "AI War Room 的資料來源、每日更新時間與營運成本說明。",
  intro1: "個人整理的 AI 戰情室，共",
  introCount: (cats: number, sources: number) => `${cats} 類、${sources} 個來源`,
  introSince: (since: string) => `。本站顯示 ${since} 起的資料，更早的每日報告在 `,
  introEnd: "。",
  scheduleHeading: "每日更新時間（台北時間）",
  hostingBefore: "網站是放在 Cloudflare Workers 上的靜態頁面，每次更新資料後重新部署。",
  hostingAfter: " 公開 Gemini 的 token 估算成本，以及 X API（貼文與帳號查詢）、Jev 與訂閱的實際花費。",
  allSources: "所有來源",
  sourceCount: (n: number) => `${n} 個來源`,
  credit: ["由 ", " 製作。"] as [string, string],
  region: { us: "美國", china: "中國", europe: "歐洲", other: "其他" } as Record<string, string>,
  openness: { open: "開放權重", closed: "閉源", mixed: "混合" } as Record<string, string>,
  labDesc: (tier: number, region: string, openness: string) => `第 ${tier} 級 · ${region} · ${openness}`,
  schedule: [
    ["17:30", "Labs：實驗室官方 X 貼文與每日快報"],
    ["17:35", "候選新聞：Jev 篩選更廣的來源"],
    ["17:40", "Podcasts：新集數的重點與逐字稿"],
    ["18:00", "每日快報：最多等 AINews 到 21:00，寫完後更新網站並發 WhatsApp 摘要"],
    ["21:30", "備援：快報當天沒跑完時，照樣更新網站的其他資料"],
  ] as [string, string][],
  cats: {
    daily: {
      category: "每日快報",
      note: "每天 18:00 開始整理，AINews 當天還沒出刊時最多等到 21:00，再把這四份電子報加上最多 15 則候選新聞寫成快報。全文在 Reports，引用的新聞列在 Sources，WhatsApp 群組會收到摘要與連結。",
      ainewsDesc: "含付費全文",
    },
    papers: {
      category: "論文",
      note: "Hugging Face 每日論文依研究方向評分，高分的論文會列進快報的建議深讀；Trending 的論文榜來自 alphaXiv。",
      alphaxivDesc: "熱門與最受喜愛，近 7 天",
    },
    candidates: {
      category: "候選新聞",
      note: "更廣的來源每天 17:35 先用 Jev 篩掉重複與舊聞，最多 15 則併進當天的快報。",
    },
    labs: {
      category: "前沿實驗室",
      note: "只收各前沿實驗室官方 X 帳號的貼文，每天 17:30 整理成 Labs 的每日快報，每週一另外產生 Labs 週報。",
    },
    reading: {
      category: "深讀",
      note: "這四份電子報每天早上由 knowledge-api 整理成分段重點，Reading 列出最近 120 天；Berkeley RDI 也是週報的素材。",
      bytebytego: "每週約 5 封",
      dailydose: "每週 1 到 2 封",
      berkeley: "Agentic AI Weekly，每週三",
      explainthis: "全端開發雙週報",
    },
    podcast: {
      category: "Podcast",
      note: "每天 17:40 檢查新集數，整理中文重點與逐字稿，放在 Podcasts。",
    },
    leaderboard: {
      category: "排行榜",
      note: "每天跟著網站資料一起更新。",
    },
  },
};
const en: typeof zh = {
  title: "About",
  description: "Data sources, daily update times and running costs of AI War Room.",
  intro1: "A personal AI war room with",
  introCount: (cats, sources) => `${cats} categories and ${sources} sources`,
  introSince: (since) => `. This site shows data from ${since} onward; earlier daily reports are in the `,
  introEnd: ".",
  scheduleHeading: "Daily update times (Taipei time)",
  hostingBefore: "The site is a static page hosted on Cloudflare Workers and is redeployed after every data update.",
  hostingAfter: " publishes the estimated Gemini token cost, plus the actual spend on the X API (posts and account lookups), Jev and subscriptions.",
  allSources: "All sources",
  sourceCount: (n) => `${n} sources`,
  credit: ["Made by ", "."],
  region: { us: "US", china: "China", europe: "Europe", other: "Other" },
  openness: { open: "Open weights", closed: "Closed", mixed: "Mixed" },
  labDesc: (tier, region, openness) => `Tier ${tier} · ${region} · ${openness}`,
  schedule: [
    ["17:30", "Labs: official X posts from the labs and the daily brief"],
    ["17:35", "Candidate news: Jev screens the wider sources"],
    ["17:40", "Podcasts: highlights and transcripts of new episodes"],
    ["18:00", "Daily digest: waits for AINews until 21:00 at most, then updates the site and sends a WhatsApp summary"],
    ["21:30", "Fallback: if the digest has not finished that day, the rest of the site data is updated anyway"],
  ],
  cats: {
    daily: {
      category: "Daily digest",
      note: "Starts at 18:00 each day, waiting until 21:00 at most if that day's AINews has not been published yet, then writes the digest from these four newsletters plus up to 15 candidate news items. The full text is in Reports, the cited news is listed in Sources, and the WhatsApp group receives a summary with a link.",
      ainewsDesc: "Includes paid full text",
    },
    papers: {
      category: "Papers",
      note: "Hugging Face Daily Papers are scored by research area, and high-scoring papers are listed under the digest's suggested deep reads; the paper rankings in Trending come from alphaXiv.",
      alphaxivDesc: "Hot and most liked, last 7 days",
    },
    candidates: {
      category: "Candidate news",
      note: "At 17:35 each day Jev filters duplicates and old news out of these wider sources, and up to 15 items are merged into that day's digest.",
    },
    labs: {
      category: "Frontier labs",
      note: "Only posts from each frontier lab's official X account are collected. They are compiled into the Labs daily brief at 17:30 each day, and a Labs weekly report is generated separately every Monday.",
    },
    reading: {
      category: "Reading",
      note: "Every morning knowledge-api turns these four newsletters into sectioned highlights, and Reading lists the last 120 days; Berkeley RDI is also material for the weekly report.",
      bytebytego: "About 5 issues a week",
      dailydose: "1 to 2 issues a week",
      berkeley: "Agentic AI Weekly, every Wednesday",
      explainthis: "Biweekly full-stack development newsletter",
    },
    podcast: {
      category: "Podcast",
      note: "New episodes are checked for at 17:40 each day; Chinese highlights and transcripts are produced and placed in Podcasts.",
    },
    leaderboard: {
      category: "Leaderboards",
      note: "Updated every day together with the site data.",
    },
  },
};
export const aboutUI = { zh, en };
