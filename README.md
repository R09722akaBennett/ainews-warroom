# AI War Room · bennettlabs.dev

個人的 AI 戰情室網站，部署在 <https://ainews-warroom.vercel.app>。Astro 5 靜態站，
資料是 bennett-hub 上各排程產生的 JSON，push 到 `main` 後 Vercel 自動部署。

## 資料從哪來

| 時間 | 排程 | 產出 |
|---|---|---|
| 16:00 | `pipeline/labs.sh` | 前沿實驗室新聞與分類，週一加 Labs 週報 |
| 16:30 | `~/wiki/tools/daily-news.sh` | 每日快報 → 呼叫 site-data.sh 更新網站 → 網站上線後發 WhatsApp 摘要 |
| 16:50 | `pipeline/candidates.sh` | Jev 篩過的候選新聞（觀察期，只寫本機紀錄） |
| 17:30 | `pipeline/site-data.sh --push` | 備援：快報沒跑時補更新網站資料 |
| 週一 09:00 | `~/wiki/tools/weekly-digest.sh` | 週報 |
| 每月 1 號 09:20 | `~/wiki/tools/weekly-digest.sh periodic` | 產業月報，季初加季報 |

wiki 是日報、週報、月報與季報的正本；`pipeline/export/from_wiki.py` 把它們轉成
`src/data/reports.json` 與 `src/data/summaries.json`。

## 目錄

```
pipeline/
  candidates/   Jev 候選新聞：收集、去重、評分
  labs/         前沿實驗室追蹤（清單在 labs/config.py）
  leaderboard/  arena.ai、alphaXiv、MCP Market 爬蟲
  export/       from_wiki.py（日報與週月季報）、labs.py（Labs 頁資料）
  sources/      候選新聞用的 RSS、Hacker News、Lobsters、Google News
  db/           SQLite（warroom.db，只在 bennett-hub）
src/            Astro 網站
backup/         公司時期的舊 issue 原始檔，封存用
```

## 本機開發

```bash
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # astro check + build，Pagefind 索引在建置時產生
```

在 bennett-hub 上建置需要加大 Node heap：

```bash
NODE_OPTIONS=--max-old-space-size=3072 pnpm build
```

只想看資料變化、不 commit 也不 push：

```bash
pipeline/site-data.sh
```
