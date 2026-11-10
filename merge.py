"""Combine hand-curated listings with freshly scraped ones into jobs.json."""
import json, os
cur = json.load(open("curated.json"))
scr = json.load(open("scraped.json")) if os.path.exists("scraped.json") else []
seen, out = set(), []
for j in scr + cur:          # scraped first so fresher data wins
    k = (j["employer"].lower(), j["title"].lower(), j["location"].lower())
    if k not in seen:
        seen.add(k); out.append(j)
json.dump(out, open("jobs.json", "w"), ensure_ascii=False, indent=1)
print(f"{len(out)} jobs ({len(scr)} scraped, {len(cur)} curated)")
