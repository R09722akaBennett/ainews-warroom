# KDAN AI War Room

AI intelligence dashboard for KDAN Mobile. Collects, compresses, and presents daily AI news with strategic analysis.

## Architecture

```
Pipeline (Mac Studio)              Website (Vercel)
─────────────────────              ────────────────
python -m agent                    src/data/*.json → Astro SSG
python -m competitor                     ↑
python -m compress auto                  │
python -m export                         │
python -m leaderboard ───────────────────┘ (git push triggers deploy)
        ↓
   warroom.db (SQLite, stays on Mac Studio)
```

- **Single source of truth**: `pipeline/warroom.db` (SQLite)
- **Website data**: `src/data/reports.json`, `summaries.json`, `sources.json`, `legacy.json`, `leaderboard.json`, `papers.json`, `competitors.json`
- **Site framework**: Astro 5 + Tailwind CSS v4, deployed on Vercel
- **LLM**: Google Gemini (`gemini-3-flash-preview` via `google.genai`)

## Pipeline (`pipeline/`)

### Module Structure

```
pipeline/
├── agent/          # Daily report workflow (collector → LLM → save)
├── competitor/     # Competitor tracker (collect → classify → weekly report)
├── compress/       # Periodic compression (warroom + industry tracks)
├── db/             # SQLite data layer (digests, summaries, raw_items, competitor_items)
├── export/         # DB → JSON for website
├── leaderboard/    # Arena AI leaderboard + alphaxiv trending papers scrapers
├── prompts/        # All LLM prompts (agent + compress + competitor)
├── sources/        # News source modules (80+ sources)
├── config.py       # Source definitions and settings
├── models.py       # Pydantic data models
└── daily.sh        # Cron orchestrator (7 steps)
```

### Running the Pipeline

```bash
cd pipeline
uv run python -m agent                     # collect news + generate report
uv run python -m competitor                # collect + classify competitor news
uv run python -m competitor --classify     # also generate competitor weekly report
uv run python -m compress auto             # auto-detect weekly/monthly/quarterly
uv run python -m export                    # DB → JSON
uv run python -m leaderboard              # arena.ai leaderboard + alphaxiv papers
```

### Daily Pipeline Flow (daily.sh)

1. **Agent** — Collect 80+ sources → deduplicate → 3-day age filter → sort by date → LLM report
2. **Competitor** — Collect 14 competitors (Google News + RSS) → classify with LLM (daily)
3. **Compress** — Auto-detect weekly (Mon) / monthly (1st) / quarterly; Mon also generates competitor weekly report
4. **Export** — DB → JSON for website
5. **Leaderboard** — Scrape arena.ai (9 categories) + alphaxiv (Hot/Likes top 20)
6. **Notify** — Send to Mattermost (optional)
7. **Git push** — Triggers Vercel deploy

### News Collection & Filtering

- **Deduplication**: same-day URL dedup + cross-day dedup (past 7 days)
- **3-day age filter**: items with `published_at` older than 3 days are removed
- **Date sorting**: items sorted by `published_at` descending before passing to LLM
- **Token tracking**: input/output/total tokens logged per LLM call and stored in DB

### Dual Compression Tracks

- **Warroom** (`weekly`/`monthly`/`quarterly`): KDAN-focused strategic summaries
- **Industry** (`raw_weekly`/`raw_monthly`/`raw_quarterly`): Unfiltered AI overview

### Competitor Tracker

- **14 competitors**: Adobe, DocuSign, Foxit, Smallpdf, PandaDoc, Canva, Notion, HubSpot, Mailchimp, Jasper, Copy.ai, Hootsuite, Buffer, SEMrush
- **Daily**: Collect via Google News + 6 RSS feeds → classify with Gemini (1 call per company)
- **Weekly (Mon)**: Per-company summary (1 call each) → combined weekly report (1 call)
- **Classification categories**: product_launch, pricing, acquisition, partnership, hiring, funding, strategy, legal, other
- **ref-N system**: Weekly report references link to individual items on /competitors page

### News Sources (80+)

- Hacker News, Reddit (12 subs), RSS (55 feeds), ArXiv (6 categories)
- GitHub Trending, Google News (3 AI queries), Lobsters, Product Hunt

### External Data Scrapers

- **Arena AI Leaderboard** (`leaderboard/scraper.py`): 9 category pages (Text, Code, Vision, etc.) + full cross-category rankings → `leaderboard.json`
- **alphaxiv Trending Papers** (`leaderboard/alphaxiv.py`): Hot 20 + Likes 20 with AI summaries → `papers.json`

## Website (`src/`)

### Pages

| Route | Content |
|-------|---------|
| `/` | Dashboard: At a Glance (2+3 card grid: models, labs, repos, products, papers) + latest briefing + trends + recent reports |
| `/reports/` | All daily reports grouped by year/month, searchable by title/tags, +N overflow indicator |
| `/reports/[date]` | Single report with ref-N links → collapsible sources section |
| `/sources` | Daily raw news sources by date/source (normalized: Google News, ArXiv) |
| `/leaderboard` | Arena AI rankings: Overview, Lab Ranking (F1 scoring), 9 category tabs with search |
| `/trending` | Tabbed: GitHub Repos (live RSS) + Product Hunt (build-time) + Papers (alphaxiv Hot/Likes with category filter + summaries) |
| `/competitors` | Competitor intelligence: weekly reports (with ref links) + classified items by company/category |
| `/trends` | Industry / KDAN Warroom tabs, each with W/M/Q period sub-tabs |
| `/analytics` | Token cost dashboard + tag trend timeline (Chart.js) + source quality table — global time range control |
| `/archive` | Historical issues (2023-2026) with company/model tags |
| `/archive/[date]` | Full content of historical issues |

### Report Features

- **ref-N system**: LLM assigns ref-N to each news source in the prompt. In the report, `ref-29` scrolls to the Sources section, highlights the item for 2 seconds. Users click through to the original source from there.
- **Sources section**: Collapsed by default, auto-opens on ref click. Lists all prompt items in order with ref-ID, source tag, title, and external link.
- **Token usage**: Displays input/output/total tokens per report.
- **ref normalization**: Handles mixed formats like `(29, ref-184)` → unified `(ref-29, ref-184)`

### Leaderboard Features

- **9 category tabs**: Text, Code, Vision, Document, Text-to-Image, Image Edit, Search, Text-to-Video, Image-to-Video — each with full model list, ELO scores, CI, price, context, rank spread
- **Lab Ranking**: F1 points system (Top 10 models earn 25/18/15/12/10/8/6/4/2/1 points per org)
- **Overview**: Cross-category rankings with sortable columns
- **Org inference**: Model name → organization mapping (35+ prefix rules + SVG title + secondary span)
- **ELO column**: Fixed-width score + CI alignment, CSS tooltip on headers

### Analytics Features

- **Token Cost Dashboard**: Summary cards (input/output/total/cost) + stacked bar chart + detailed breakdown table — all JS-driven, filtered by task type (Daily/Weekly/Monthly/Quarterly/Comp. Classify/Comp. Weekly)
- **Tag Trends**: Chart.js line chart with cumulative mentions, custom scrollable tag list (replaces default legend), type filters (Companies/Models/Topics)
- **Source Quality**: Collected vs referenced table with rate bars and hover tooltips
- **Global time range**: 7d/30d/90d/All quick buttons + custom date picker, controls all three sections

### Design System

- **Fonts**: Geist Sans (body) + Geist Mono (metadata/dates)
- **Colors**: CSS custom properties with light/dark/system toggle
  - Accent warm (amber): KDAN/warroom elements
  - Accent cool (cyan): industry/model elements
  - Accent purple: trending repos / paper categories
  - Accent orange: Product Hunt
  - Period colors: emerald (quarterly), blue (monthly), cyan (weekly)
- **Tags**: purple (companies), cyan (models), amber (topics)
- **Shared components**: `tab-pill` (unified tabs), `ExternalIcon`, `card` system with accent variants
- **Rank colors**: gold (#1), silver (#2), bronze (#3), cyan (top 10) — defined globally
- **Nav**: Active page indicator on header links

### Development

```bash
npm install
npm run dev          # Dev server at localhost:4321
npm run build        # Production build
```

## Environment Variables

```bash
GOOGLE_API_KEY=...              # Required for Gemini LLM
GEMINI_MODEL=gemini-3-flash-preview  # Optional, this is the default
REDDIT_CLIENT_ID=...            # Optional, for Reddit source
REDDIT_CLIENT_SECRET=...        # Optional, for Reddit source
MATTERMOST_URL=...              # Optional, for Mattermost notification
MATTERMOST_TOKEN=...            # Optional, for Mattermost notification
```

## Key Decisions

- DB-driven website (not markdown files) to keep build size small
- Dual compression tracks for KDAN strategic needs and AI industry overview
- Astro SSG for fast, static deployment on Vercel
- Pipeline runs on Mac Studio, pushes JSON to repo, Vercel auto-deploys
- Workflow architecture (not Agent) — one LLM call per report, deterministic flow
- Tags (companies/models/topics) generated by LLM for visual filtering
- 80+ news sources across HN, Reddit, RSS, ArXiv, GitHub, Google News, Lobsters, Product Hunt
- ref-N links are in-page anchors (not direct external links) for user control
- Token usage tracked across all LLM calls for cost transparency
- Arena leaderboard + alphaxiv papers scraped daily alongside news pipeline
- Lab ranking uses F1 points to reflect overall org strength, not just best single model
- 3-day age filter ensures freshness while allowing cross-day dedup window
- Competitor tracker: daily collect (HTTP) + daily classify (LLM) + weekly report (Mon)
- Competitor weekly report uses 2-step LLM: per-company summaries → combined report for precision + global view
- Source names normalized (Google News, ArXiv) for cleaner grouping
- Analytics uses Chart.js via CDN to avoid npm dependency bloat
