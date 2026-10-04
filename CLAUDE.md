# AI War Room · bennettlabs.dev

開發慣例見 ~/playbook（AGENTS.md 與 skills/）；本檔只放這個專案的事實。

## Project

- The owner is the only person who works in this repo. The site it builds is
  public and read by outsiders.
- Astro 5 static site served as Cloudflare Workers static assets at
  `https://aiwarroom.bennettlabs.dev`. Every push to `main` triggers a Workers
  Builds deploy; there is no other deploy path. README.md has the cron schedule
  and the data flow.
- The wiki (`bennett-hub:~/wiki`) is the source of truth for daily digests and
  the weekly, monthly and quarterly reports. `pipeline/export/from_wiki.py`
  rebuilds `src/data/reports.json` and `src/data/summaries.json` from it.
- `pipeline/warroom.db` exists only on bennett-hub and holds lab items and
  candidate raw items from 2026-09-01 on (the lab posts were backfilled from the
  X API). It has no daily reports.
- Reports up to 2026-09-08 came from the retired company agent. from_wiki keeps
  them as an archive and strips their company strategy sections on every run.
- The Postgres database behind knowledge-api is named `kdan`; that name is
  real, not leftover branding.

## External writes

Each of these changes something outside the working tree. Run the dry run
first and say which flag you are about to use.

- `git push` to `main` deploys the public site.
- `pipeline/labs.sh` reads the paid X API, calls Gemini and writes to
  knowledge-api.
- `pipeline/candidates.sh` calls Jev (TypeSafe, paid) and Gemini.
- `pipeline/podcasts.sh` fetches episodes with the owner's Substack cookie
  (falling back to the subscriber mail over read-only Gmail IMAP), calls
  Gemini and writes to knowledge-api.
- `pipeline/site-data.sh --push` commits the data files and pushes `main`.
- `labs.sh`, `candidates.sh` and `podcasts.sh` are dry runs without `--live`;
  `site-data.sh` is a dry run without `--push`.
- The WhatsApp send lives in the wiki repo (`~/wiki/tools/send_digest.py`),
  not here.

## Commands

- Site: `pnpm build` (`astro check` plus build). On bennett-hub it needs
  `NODE_OPTIONS=--max-old-space-size=3072`.
- Pipeline tests: `cd pipeline && uv run --no-sync python -m unittest discover -s tests`.
- Exporters: `cd pipeline && uv run --no-sync python -m export.<name>`.
- Secrets are in `~/infra/.env` on the VPS and the shell wrappers load it;
  `pipeline/.env.example` lists the variable names.
- `src/data/*.json` is generated and committed by `site-data.sh`;
  `pipeline/data/` is gitignored run state.

## Conventions

- pnpm, never npm.
- Shell wrapper header comments are in Chinese.
- Commits that touch `src/data` are made by `site-data.sh` with its fixed
  Chinese subject; do not hand-edit those files.
- UI language: English navigation and page names, Traditional Chinese in-page
  copy.
- No `<header>` elements inside pages; `global.css` applies the site-header
  styling to every `header`.
- Internal links never end with `/`.
- Summaries periods in use: `raw_weekly`, `raw_monthly`, `raw_quarterly`
  (industry, from the wiki) and `labs_daily`, `labs_weekly`, `labs_classify`.
  from_wiki drops the retired company periods on every run.
