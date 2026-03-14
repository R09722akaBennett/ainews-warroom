# KDAN AI War Room

AI intelligence dashboard for KDAN Mobile. Automatically collects AI news from 80+ sources, generates strategic reports with LLM analysis, and compresses insights into weekly/monthly/quarterly summaries.

## Architecture

```
Mac Studio (cron daily)              Vercel (static site)
───────────────────────              ───────────────────
python -m agent                      src/data/*.json → Astro SSG
python -m compress auto                    ↑
python -m export ──────────────────────────┘ (git push triggers deploy)
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
```

## Project Structure

```
├── src/                          # Astro website
│   ├── pages/
│   │   ├── index.astro           # Dashboard
│   │   ├── reports/              # Daily report pages
│   │   ├── sources.astro         # Raw news sources
│   │   ├── trending.astro        # GitHub Trending (live)
│   │   ├── trends.astro          # W/M/Q summaries
│   │   └── archive/              # Historical issues (2023-2026)
│   ├── components/
│   ├── data/                     # JSON exported from DB
│   └── styles/
│
├── pipeline/                     # News collection + AI analysis
│   ├── agent/                    # Daily report workflow
│   │   ├── runner.py             # Main workflow (collect → LLM → save)
│   │   ├── collector.py          # News collection from all sources
│   │   └── context.py            # Historical context loading
│   ├── compress/                 # Periodic compression (W/M/Q)
│   │   ├── warroom.py            # KDAN-focused track
│   │   └── industry.py          # Industry-wide track
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
│   └── daily.sh                  # Cron orchestrator
```

## Data Flow

```
80+ Sources (HN, Reddit, RSS, ArXiv, GitHub, Google News, Lobsters, PH)
    ↓ collect (python -m agent)
raw_daily_items → sources.json      ← browsable on /sources
    ↓ LLM (Gemini)
daily_digests → reports.json        ← daily reports with tags on /reports
    ↓ compress (python -m compress)
periodic_summaries → summaries.json ← W/M/Q trends on /trends
```

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=...                   # Gemini LLM

# Optional
REDDIT_CLIENT_ID=...                 # Reddit API
REDDIT_CLIENT_SECRET=...
GEMINI_MODEL=gemini-3-flash-preview  # defaults to this
```

## Tech Stack

- **Website**: Astro 5, Tailwind CSS v4, Vercel
- **Pipeline**: Python 3.12, Google Gemini, SQLite
- **LLM**: `gemini-3-flash-preview` (configurable)
