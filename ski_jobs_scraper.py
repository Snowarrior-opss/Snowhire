#!/usr/bin/env python3
"""
Snowhire scraper: collects ski-resort jobs from public sources and writes jobs.json
in the same format the Snowhire website uses.

Python 3.9+, standard library only.   Run:  python3 ski_jobs_scraper.py

How it stays polite and legal:
  * Only uses public JSON APIs (Greenhouse, Lever) and RSS/Atom feeds that employers publish.
  * Checks robots.txt before fetching any non-API URL.
  * Waits between requests and identifies itself with a User-Agent.
  * Does NOT scrape sites whose terms forbid it (Indeed, Glassdoor, LinkedIn, etc.).
    Use their official feeds/partner APIs if you have access.

To add an employer, add a line to SOURCES. Find the token in the employer's careers URL:
  Greenhouse: boards.greenhouse.io/<TOKEN>      Lever: jobs.lever.co/<TOKEN>
"""
import json, re, time, hashlib, urllib.request, urllib.parse, urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import date

USER_AGENT = "SnowhireBot/1.0 (+contact: you@example.com)"   # <- put your real contact here
DELAY = 2.0          # seconds between requests
OUT_FILE = "scraped.json"

# (kind, token_or_url, employer name, default location, default region)
SOURCES = [
    # ("greenhouse", "examplemountain", "Example Mountain Resort", "Colorado, USA", "North America"),
    # ("lever",      "examplealps",     "Example Alps Co",         "Chamonix, France", "Europe"),
    # ("rss",        "https://example.com/careers/feed.xml", "Example Ski Area", "Hokkaido, Japan", "Asia"),
]

# A posting is kept only if its title/description matches one of these.
KEYWORDS = ["ski", "snowboard", "lift", "snowmak", "patrol", "chalet", "terrain park", "resort",
            "snow school", "snowsports", "rental", "slope", "mountain", "grooming", "snowcat", "avalanche"]

CATEGORIES = [  # first match wins
    ("Ski Patrol", ["patrol", "avalanche"]),
    ("Instruction", ["instructor", "snow school", "snowsports", "coach", "ski school"]),
    ("Snowmaking", ["snowmak", "snow making"]),
    ("Terrain Park", ["terrain park", "park crew"]),
    ("Lifts & Mountain Ops", ["lift", "gondola", "snowcat", "groom", "mountain ops", "dispatch"]),
    ("Retail & Rental", ["rental", "retail", "ski tech", "boot fit", "valet"]),
    ("Childcare", ["childcare", "nanny", "kids", "daycare"]),
    ("Guiding", ["guide"]),
    ("Guest Services", ["guest", "front desk", "reservation", "concierge", "bell"]),
    ("Hospitality", ["chef", "cook", "bartender", "server", "housekeep", "chalet", "kitchen", "barista", "f&b"]),
    ("Maintenance", ["maintenance", "mechanic", "snow removal", "snow clearing", "electrician"]),
]

_robots = {}

def allowed(url):
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)

def fetch(url, check_robots=False):
    if check_robots and not allowed(url):
        print(f"  robots.txt disallows {url}, skipping")
        return None
    time.sleep(DELAY)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  failed {url}: {e}")
        return None

def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def categorize(text):
    t = text.lower()
    for name, words in CATEGORIES:
        if any(w in t for w in words):
            return name
    return "Various"

def season_for(region, text):
    t = text.lower()
    if any(w in t for w in ["southern winter", "june", "july", "august"]) and region == "Oceania":
        return "Southern winter"
    return "Southern winter" if region in ("Oceania", "South America") else "Northern winter"

def make(title, employer, location, region, url, source, desc=""):
    blob = f"{title} {desc}"
    if not any(k in blob.lower() for k in KEYWORDS):
        return None
    return {
        "title": title.strip(), "employer": employer, "location": location or "",
        "region": region, "category": categorize(title + " " + desc[:300]),
        "season": season_for(region, blob), "source": source, "url": url,
        "found": date.today().isoformat(),
    }

def from_greenhouse(token, employer, loc, region):
    raw = fetch(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    for j in (json.loads(raw).get("jobs", []) if raw else []):
        job = make(j["title"], employer, (j.get("location") or {}).get("name") or loc, region,
                   j["absolute_url"], "Greenhouse")
        if job: yield job

def from_lever(token, employer, loc, region):
    raw = fetch(f"https://api.lever.co/v0/postings/{token}?mode=json")
    for j in (json.loads(raw) if raw else []):
        where = (j.get("categories") or {}).get("location") or loc
        job = make(j["text"], employer, where, region, j["hostedUrl"], "Lever", j.get("descriptionPlain", ""))
        if job: yield job

def from_rss(url, employer, loc, region):
    raw = fetch(url, check_robots=True)
    if not raw:
        return
    root = ET.fromstring(raw)
    for it in root.iter():
        if it.tag.endswith("item") or it.tag.endswith("entry"):
            g = lambda n: next((c for c in it if c.tag.endswith(n)), None)
            t, l, d = g("title"), g("link"), g("description") or g("summary")
            link = (l.text or l.get("href")) if l is not None else None
            if t is not None and link:
                job = make(t.text or "", employer, loc, region, link.strip(), "Careers feed", strip_html(d.text if d is not None else ""))
                if job: yield job

HANDLERS = {"greenhouse": from_greenhouse, "lever": from_lever, "rss": from_rss}

def main():
    jobs, seen = [], set()
    for kind, ref, employer, loc, region in SOURCES:
        print(f"{employer} ({kind})")
        for job in HANDLERS[kind](ref, employer, loc, region):
            key = hashlib.md5((job["employer"] + job["title"] + job["location"]).lower().encode()).hexdigest()[:12]
            if key not in seen:
                seen.add(key)
                job["id"] = key
                jobs.append(job)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(jobs)} jobs to {OUT_FILE}")

if __name__ == "__main__":
    main()
