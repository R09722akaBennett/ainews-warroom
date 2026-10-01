# AI War Room · bennettlabs.dev

個人的 AI 戰情室網站，給外部讀者看，網址 <https://aiwarroom.bennettlabs.dev>。
Astro 5 靜態站，跑在 Cloudflare Workers 靜態資產上，push 到 `main` 後由 Workers Builds 自動部署。
資料是 bennett-hub 上各排程產生的 JSON。

## 資料從哪來

排程都在 bennett-hub 的 cron，時區 Asia/Taipei。

| 時間 | 排程 | 產出 |
|---|---|---|
| 17:30 | `pipeline/labs.sh` | 實驗室官方 X 貼文 → 分類 → Labs 日報，週一加週報 |
| 17:35 | `pipeline/candidates.sh` | 廣來源（含 Google News）經 Jev 評分 → `pipeline/data/candidates/<date>.json`，快報會讀 |
| 17:40 | `pipeline/podcasts.sh` | Latent Space 節目：逐字稿、中文結構化摘要 → `pipeline/data/podcasts/` |
| 18:00 | `~/wiki/tools/daily-news.sh` | 等 AINews（最晚到 21:00）寫每日快報 → 呼叫 `site-data.sh --push` → 發 WhatsApp 摘要 |
| 21:30 | `pipeline/site-data.sh --push` | 備援：快報沒跑時補更新網站資料 |
| 週一 09:00 | `~/wiki/tools/weekly-digest.sh` | 週報 |
| 每月 1 號 09:20 | `~/wiki/tools/weekly-digest.sh periodic` | 產業月報，季初加季報 |

wiki 是日報、週報、月報與季報的正本。`site-data.sh` 依序跑 `export.from_wiki`、`export.labs`、
`export.reading`、`export.costs`、`export.podcasts` 與 `leaderboard`，把結果寫進 `src/data/*.json` 再 commit、push。

來源：AINews（Latent Space feed，付費全文經 Gmail 取得）、TLDR AI、TechCrunch、Import AI、Jev 篩過的候選新聞；
Labs 只收各實驗室的官方 X 貼文；Reading 的電子報（ByteByteGo、Daily Dose of DS、Berkeley RDI、ExplainThis）經 knowledge-api 進來；
另有 HF daily papers、arena.ai 排行、alphaxiv、MCP Market。

## 頁面

Reports、Sources、Insights、Reading（含單篇頁）、Podcasts（含單集頁）、Leaderboard、Trending、Labs、
Analytics（含 Gemini、X、Jev 與訂閱的運行成本）、Archive、About。

## 目錄

```
pipeline/
  candidates/   Jev 候選新聞：收集、去重、評分
  labs/         前沿實驗室追蹤（清單在 labs/config.py）
  podcasts/     Latent Space 逐字稿與摘要
  leaderboard/  arena.ai、alphaXiv、MCP Market 爬蟲
  export/       from_wiki.py、labs.py、reading.py、costs.py、podcasts.py，各自產一份 src/data JSON
  sources/      候選新聞用的 RSS、Hacker News、Lobsters、Google News
  db/           SQLite（warroom.db，只在 bennett-hub）
  data/         排程的本機狀態，gitignored
src/data/       網站資料 JSON，由 site-data.sh 產生並 commit
src/            Astro 網站
```

密鑰放在 VPS 的 `~/infra/.env`，shell wrapper 會自己載入；`pipeline/.env.example` 列出需要的變數名稱。

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
