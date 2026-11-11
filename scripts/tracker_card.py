#!/usr/bin/env python3
"""Write a live India Threat Tracker summary into README.md.

Reads the public watchlist feed and replaces whatever sits between
<!-- TRACKER:START --> and <!-- TRACKER:END --> in README.md. Run daily by
.github/workflows/tracker-card.yml. If the feed can't be read, the README is
left as it is.

    python scripts/tracker_card.py               # fetch the live feed
    python scripts/tracker_card.py --file f.json # use a saved copy
"""
import datetime as dt
import json
import re
import sys
import urllib.request

FEED = "https://raw.githubusercontent.com/sohankanna/india-threat-tracker/main/data/watchlist.json"
TRACKER = "https://www.sohankanna.com/tracker"
README = "README.md"
START, END = "<!-- TRACKER:START -->", "<!-- TRACKER:END -->"


def product(i):
    v, p = i["vendor"].strip(), i["product"].strip()
    label = p if p.lower().startswith(v.lower()) else f"{v} {p}"
    if len(label) > 38 and " and " in label:
        label = label.split(" and ")[0]
    return re.sub(r" Software$", "", label)


def epss(i):
    e = i.get("epss")
    if e is None:
        return "—"
    return f"{int(e * 100)}%" if e >= 0.1 else f"{e * 100:.1f}%"


def render(feed):
    items = feed["items"]
    updated = dt.datetime.fromisoformat(feed["generated_at"].replace("Z", "+00:00"))
    since = (updated - dt.timedelta(days=7)).date().isoformat()
    week = [i for i in items if i["date_added"] >= since]
    high = [i for i in week if i["india_relevance"] == "high"]
    newest = sorted((i for i in items if i["india_relevance"] == "high"),
                    key=lambda i: (i["date_added"], i.get("epss") or 0), reverse=True)[:4]
    rows = "\n".join(
        f"| [`{i['cve']}`]({TRACKER}/vulnerabilities?cve={i['cve']}) | {product(i)}"
        f"{' · ransomware' if i.get('known_ransomware') else ''} | {i['date_added']} | {epss(i)} |"
        for i in newest
    )
    return f"""{START}
<div align="center">

**{len(week)}** India-relevant flaws added to CISA KEV in the last 7 days · **{len(high)}** high relevance · **{len(items)}** on the watchlist

| Newest high-relevance | Product | Added to KEV | EPSS |
| :--- | :--- | :--- | :---: |
{rows}

<sub>Auto-updated daily from the [India Threat Tracker]({TRACKER}) · feed generated {updated:%d %b %Y, %H:%M} UTC</sub>

</div>
{END}"""


def main(argv):
    try:
        if "--file" in argv:
            with open(argv[argv.index("--file") + 1], encoding="utf-8") as f:
                feed = json.load(f)
        else:
            req = urllib.request.Request(FEED, headers={"User-Agent": "sohankanna-profile-readme"})
            with urllib.request.urlopen(req, timeout=60) as r:
                feed = json.load(r)
        block = render(feed)
    except Exception as e:  # never break the profile because the feed hiccupped
        print(f"::warning::Tracker feed unavailable ({e}); README left unchanged")
        return 0
    with open(README, encoding="utf-8") as f:
        text = f.read()
    if START not in text or END not in text:
        print("::error::TRACKER markers missing from README.md")
        return 1
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("No change")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
