# ITSKHAY Backlink Generation Agent

A free, no-API Python workflow that discovers potential backlink opportunities through public DuckDuckGo HTML search results, performs cautious checks on a limited batch, and exports a review-only CSV.

## What it does

- Uses built-in queries for directories, agency listings, guest posts, portfolios, and resource pages.
- Uses Python's standard library only. No AI API key, paid package, or external database is required.
- Attempts to respect each target page's `robots.txt` before fetching it.
- Creates a CSV with URL, domain, category, page title, discovery query, status, and review notes.
- Never submits forms, creates accounts, emails site owners, or purchases links.

## Run it on GitHub

1. Open the **Actions** tab.
2. Select **Free Backlink Prospect Agent**.
3. Click **Run workflow** and keep the default query count initially.
4. Wait for the run to finish.
5. Open the run and download the artifact named `itskhay-backlink-prospects-N`.

The workflow is manual-only by default so you can inspect the results before enabling any schedule. After testing, you can add a `schedule` trigger if you want recurring runs.

## Run on your computer

Requires Python 3.10 or newer. Run `python main.py` from the repository folder. Output is written to `output/prospects.csv`.

## Cost and limitations

- No API key or paid API is used. GitHub Actions usage is subject to GitHub's current plan limits.
- Public search engines can rate-limit requests or change their HTML, so discovery may return few or no results. This is a best-effort starter, not a guaranteed search service.
- `MAX_QUERIES` controls the number of built-in queries (up to 12). `REQUEST_DELAY_SECONDS` controls the delay between requests.
- Search results are candidates, not verified backlink opportunities. Confirm relevance, site legitimacy, submission eligibility, editorial rules, and whether the link would be useful.

## Human review and persistence

The agent never submits forms, creates accounts, emails site owners, or buys links. Avoid spam, automated submissions, and paid-link schemes.

The workflow uploads the CSV as a downloadable GitHub Actions artifact and does not commit prospect data to the repository. Artifacts are retained for 30 days. Runs do not automatically deduplicate against earlier artifacts unless the previous CSV is supplied locally at `output/prospects.csv`. A later improvement can add durable free storage if needed.
