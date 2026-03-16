# KDAN AI War Room

AI intelligence dashboard for KDAN Mobile. Automatically collects AI news from 80+ sources, generates strategic reports with LLM analysis, and compresses insights into weekly/monthly/quarterly summaries.

## Architecture

```
Mac Studio (cron daily)              Vercel (static site)
───────────────────────              ───────────────────
python -m agent                      src/data/*.json → Astro SSG
python -m compress auto                    ↑
python -m export                           │
python -m leaderboard ─────────────────────┘ (git push triggers deploy)
        ↓
   warroom.db (SQLite)
```

## Quick Start

### Website

```bash
npm install
npm run dev          # localhost:4321
npm run build        # production build
```

### Pipeline

```bash
cd pipeline
cp .env.example .env  # add your API keys
uv sync

# Full daily run
uv run python -m agent            # collect news + generate report
uv run python -m compress auto    # compress weekly/monthly/quarterly
uv run python -m export           # DB → JSON for website
uv run python -m leaderboard      # arena.ai leaderboard + alphaxiv papers
```

## Project Structure

```
├── src/                          # Astro website
│   ├── pages/
│   │   ├── index.astro           # Dashboard (At a Glance + briefing + trends)
│   │   ├── reports/              # Daily report pages (searchable, ref-N system)
│   │   ├── sources.astro         # Raw news sources by date
│   │   ├── leaderboard.astro     # Arena AI rankings + Lab Ranking (F1 scoring)
│   │   ├── trending.astro        # GitHub Repos + Product Hunt + Papers (tabbed)
│   │   ├── trends.astro          # Industry / KDAN Warroom W/M/Q sub-tabs
│   │   ├── archive/              # Historical issues (2023-2026)
│   │   └── about.astro
│   ├── components/
│   │   ├── Header.astro          # Nav with active page indicator
│   │   ├── Footer.astro          # Sitemap links
│   │   ├── ExternalIcon.astro    # Shared external link icon
│   │   └── ...
│   ├── data/                     # JSON exported from pipeline
│   │   ├── reports.json          # Daily reports with refs + token usage
│   │   ├── sources.json          # Raw news items
│   │   ├── summaries.json        # W/M/Q summaries with token usage
│   │   ├── leaderboard.json      # Arena AI model rankings (9 categories)
│   │   ├── papers.json           # alphaxiv Hot/Likes top 20
│   │   ├── legacy.json           # Historical issue metadata
│   │   └── legacy-content.json   # Historical issue full content
│   └── styles/
│       └── global.css            # Design system (tab-pill, card, rank colors)
│
├── pipeline/                     # News collection + AI analysis
│   ├── agent/                    # Daily report workflow
│   │   ├── runner.py             # Main workflow (collect → LLM → save)
│   │   ├── collector.py          # News collection + dedup + 3-day age filter
│   │   └── context.py            # Historical context loading
│   ├── compress/                 # Periodic compression (W/M/Q)
│   │   ├── warroom.py            # KDAN-focused track
│   │   ├── industry.py           # Industry-wide track
│   │   └── llm.py                # Shared Gemini call + token tracking
│   ├── leaderboard/              # External data scrapers
│   │   ├── scraper.py            # Arena AI leaderboard (9 categories + full table)
│   │   └── alphaxiv.py           # alphaxiv trending papers (Hot + Likes)
│   ├── db/                       # SQLite data layer
│   ├── export/                   # DB → JSON for website
│   ├── prompts/                  # All LLM prompts
│   ├── sources/                  # News source modules
│   │   ├── hackernews.py
│   │   ├── reddit.py
│   │   ├── rss_feeds.py          # 55 RSS feeds
│   │   ├── arxiv_source.py       # 6 categories
│   │   ├── github_trending.py
│   │   ├── google_news.py        # 3 AI search queries
│   │   ├── lobsters.py
│   │   └── producthunt.py
│   ├── config.py                 # Source definitions
│   ├── models.py                 # Pydantic data models
│   └── daily.sh                  # Cron orchestrator (6 steps)
```

## Data Flow

```
80+ Sources (HN, Reddit, RSS, ArXiv, GitHub, Google News, Lobsters, PH)
    ↓ collect + dedup + 3-day age filter (python -m agent)
raw_daily_items → sources.json         ← browsable on /sources
    ↓ LLM (Gemini) — items sorted by date, token usage tracked
daily_digests → reports.json           ← daily reports with ref-N on /reports
    ↓ compress (python -m compress)
periodic_summaries → summaries.json    ← W/M/Q trends on /trends

Arena AI (arena.ai/leaderboard/*)
    ↓ scrape 9 categories (python -m leaderboard)
leaderboard.json                       ← model rankings on /leaderboard

alphaxiv.org (Hot + Likes)
    ↓ scrape top 20 each
papers.json                            ← trending papers on /trending#papers
```

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=...                   # Gemini LLM

# Optional
REDDIT_CLIENT_ID=...                 # Reddit API
REDDIT_CLIENT_SECRET=...
GEMINI_MODEL=gemini-3-flash-preview  # defaults to this
MATTERMOST_URL=...                   # Mattermost notification
MATTERMOST_TOKEN=...
```

## Tech Stack

- **Website**: Astro 5, Tailwind CSS v4, Vercel
- **Pipeline**: Python 3.12, Google Gemini, SQLite, BeautifulSoup
- **LLM**: `gemini-3-flash-preview` (configurable)
- **Data**: arena.ai (leaderboard), alphaxiv.org (papers), 80+ news sources
