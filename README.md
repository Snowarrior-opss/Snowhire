# Snowhire

Static ski-jobs site that updates itself every day.

## Set up (about 5 minutes)
1. Create a new GitHub repository and upload everything in this folder (keep the `.github` folder).
2. Repo Settings > Pages > Source: "Deploy from a branch", branch `main`, folder `/ (root)`. Your site goes live at `https://<you>.github.io/<repo>/`.
3. Repo Settings > Actions > General > Workflow permissions: "Read and write permissions".
4. Open `ski_jobs_scraper.py`, set `USER_AGENT` to your real contact email, and add employers to `SOURCES`
   (Greenhouse token from `boards.greenhouse.io/<token>`, Lever token from `jobs.lever.co/<token>`, or an RSS feed URL).
5. Actions tab > "Update ski jobs" > Run workflow to test. After that it runs daily.

## How it works
`ski_jobs_scraper.py` > `scraped.json`; `merge.py` combines it with `curated.json` (hand-picked listings) > `jobs.json`; `index.html` reads `jobs.json`.
Edit `curated.json` by hand any time to add or remove listings.

## Post a job page
`post-job.html` has pricing and an employer form. Open it and edit the three settings at the top of its script:
- `FORM_ENDPOINT`: create a free form at formspree.io and paste its URL, so submissions arrive in your email. Leave empty to use a pre-filled email instead.
- `FALLBACK_EMAIL`: your email address.
- `PAYMENT_LINKS`: create a Payment Link for each plan in Stripe (Payment Links > New) and paste the three URLs.
When an employer pays, add their job to `curated.json` (same fields as the others) and it appears on the site.
