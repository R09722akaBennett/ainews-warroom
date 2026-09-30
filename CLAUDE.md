# AI War Room · bennettlabs.dev

Personal AI news dashboard. Astro 5 static site on Vercel (auto-deploys on push
to `main`), fed by JSON that cron jobs on bennett-hub write. See README.md for
the schedule and layout.

## Where things live

- The wiki (`bennett-hub:~/wiki`) is the source of truth for daily digests and
  the weekly, monthly and quarterly reports. `pipeline/export/from_wiki.py`
  rebuilds `src/data/reports.json` and `src/data/summaries.json` from it.
- `pipeline/warroom.db` exists only on bennett-hub and holds lab items and
  candidate raw items from 2026-10-01 on. It has no daily reports.
- Reports up to 2026-09-08 came from the retired company agent. from_wiki keeps
  them as an archive and strips their company strategy sections on every run.

## Rules

- `pipeline/site-data.sh` without `--push` is the dry run. With `--push` it
  commits only the data files and pushes `main`, which deploys production.
- Summaries periods in use: `raw_weekly`, `raw_monthly`, `raw_quarterly`
  (industry, from the wiki) and `labs_weekly`, `labs_classify`. from_wiki drops
  the retired company periods on every run.
- The Postgres database behind knowledge-api is named `kdan`; that name is
  real, not leftover branding.
- Building on bennett-hub needs `NODE_OPTIONS=--max-old-space-size=3072`.
- Python runs through uv in `pipeline/` (`uv run --no-sync python -m ...`).
