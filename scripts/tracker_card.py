#!/usr/bin/env python3
"""Draw the live India Threat Tracker panel for the profile README.

Reads the public watchlist feed, writes assets/tracker-card.svg (a small
SOC-style panel) and refreshes the block between <!-- TRACKER:START --> and
<!-- TRACKER:END --> in README.md with the image plus clickable CVE links.
Run daily by .github/workflows/tracker-card.yml. If the feed can't be read,
nothing is touched.

    python scripts/tracker_card.py               # fetch the live feed
    python scripts/tracker_card.py --file f.json # use a saved copy

To restyle the panel, change PALETTE / the layout constants below; all the
numbers come from summarise(), so the drawing and the data stay separate.
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from xml.sax.saxutils import escape

FEED = "https://raw.githubusercontent.com/sohankanna/india-threat-tracker/main/data/watchlist.json"
TRACKER = "https://www.sohankanna.com/tracker"
README = "README.md"
SVG = "assets/tracker-card.svg"
START, END = "<!-- TRACKER:START -->", "<!-- TRACKER:END -->"
ROWS = 4          # newest high-relevance flaws to list
DAYS = 30         # length of the activity strip

PALETTE = {
    "bg": "#0d1117", "panel": "#161b22", "line": "#30363d", "text": "#e6edf3",
    "muted": "#8b949e", "green": "#00ff41", "red": "#f85149", "amber": "#d29922",
    "orange": "#f0883e", "blue": "#58a6ff",
}
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# ---------------------------------------------------------------- data

def product(i):
    v, p = i["vendor"].strip(), i["product"].strip()
    label = p if p.lower().startswith(v.lower()) else f"{v} {p}"
    if len(label) > 38 and " and " in label:
        label = label.split(" and ")[0]
    label = re.sub(r" Software$", "", label)
    return label if len(label) <= 30 else label[:29] + "…"


def epss_text(e):
    if e is None:
        return "n/a"
    return f"{int(e * 100)}%" if e >= 0.1 else f"{e * 100:.1f}%"


def summarise(feed):
    items = feed["items"]
    updated = dt.datetime.fromisoformat(feed["generated_at"].replace("Z", "+00:00"))
    today = updated.date()
    since = (today - dt.timedelta(days=7)).isoformat()
    week = [i for i in items if i["date_added"] >= since]
    newest = sorted((i for i in items if i["india_relevance"] == "high"),
                    key=lambda i: (i["date_added"], i.get("epss") or 0), reverse=True)[:ROWS]
    strip = []
    for n in range(DAYS - 1, -1, -1):
        day = (today - dt.timedelta(days=n)).isoformat()
        on_day = [i for i in items if i["date_added"] == day]
        strip.append((day, sum(i["india_relevance"] == "high" for i in on_day), len(on_day)))
    return {
        "updated": updated, "today": today,
        "week": len(week),
        "week_high": sum(i["india_relevance"] == "high" for i in week),
        "ransomware": sum(bool(i.get("known_ransomware")) for i in items),
        "total": len(items),
        "strip": strip,
        "rows": newest,
    }


# ---------------------------------------------------------------- drawing

def due_chip(i, today):
    try:
        due = dt.date.fromisoformat(i["due_date"])
    except (KeyError, TypeError, ValueError):
        return "—", PALETTE["muted"]
    left = (due - today).days
    if left < 0:
        return "past due", PALETTE["red"]
    if left <= 3:
        return (f"due in {left}d" if left else "due today"), PALETTE["amber"]
    return f"due {due:%d %b}", PALETTE["muted"]


def epss_colour(e):
    if e is None:
        return PALETTE["muted"]
    return PALETTE["red"] if e >= 0.1 else PALETTE["amber"] if e >= 0.01 else PALETTE["green"]


def draw(s):
    P = PALETTE
    W = 860
    tiles = [
        ("NEW IN KEV · 7D", s["week"], P["green"]),
        ("HIGH RELEVANCE · 7D", s["week_high"], P["red"]),
        ("RANSOMWARE-LINKED", s["ransomware"], P["orange"]),
        ("ON THE WATCHLIST", s["total"], P["blue"]),
    ]
    out = []
    add = out.append
    row_y0, row_h = 262, 40
    H = row_y0 + row_h * len(s["rows"]) + 38

    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="India Threat Tracker: {s["week"]} India-relevant flaws added to CISA KEV '
        f'in the last 7 days, {s["week_high"]} high relevance, {s["total"]} on the watchlist">')
    add(f"""<style>
.m{{font-family:{MONO}}} .s{{font-family:{SANS}}}
.pulse{{animation:p 2s ease-in-out infinite}} @keyframes p{{50%{{opacity:.25}}}}
.in{{opacity:0;animation:f .5s ease-out forwards}} @keyframes f{{to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.pulse,.in{{animation:none;opacity:1}}}}
</style>""")
    add(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="{P["bg"]}" stroke="{P["line"]}"/>')

    # title bar
    add(f'<circle class="pulse" cx="26" cy="27" r="5" fill="{P["green"]}"/>')
    add(f'<text x="40" y="32" class="m" font-size="13" font-weight="700" fill="{P["green"]}" letter-spacing="1.5">LIVE</text>')
    add(f'<text x="84" y="32" class="s" font-size="15" font-weight="600" fill="{P["text"]}">India Threat Tracker</text>')
    add(f'<text x="246" y="32" class="s" font-size="13" fill="{P["muted"]}">· CISA KEV flaws that matter to India</text>')
    add(f'<text x="{W-22}" y="32" text-anchor="end" class="m" font-size="12" fill="{P["muted"]}">'
        f'feed {s["updated"]:%d %b %Y · %H:%M} UTC</text>')
    add(f'<line x1="1" y1="52" x2="{W-1}" y2="52" stroke="{P["line"]}"/>')

    # stat tiles
    tw, gap, ty = 196, 12, 68
    for n, (label, value, colour) in enumerate(tiles):
        x = 22 + n * (tw + gap)
        add(f'<g class="in" style="animation-delay:{0.1 + n * 0.08:.2f}s">')
        add(f'<rect x="{x}" y="{ty}" width="{tw}" height="74" rx="8" fill="{P["panel"]}" stroke="{P["line"]}"/>')
        add(f'<rect x="{x}" y="{ty + 14}" width="3" height="46" rx="1.5" fill="{colour}"/>')
        add(f'<text x="{x + 16}" y="{ty + 26}" class="m" font-size="10.5" fill="{P["muted"]}" letter-spacing=".8">{label}</text>')
        add(f'<text x="{x + 16}" y="{ty + 60}" class="s" font-size="28" font-weight="700" fill="{colour}">{value}</text>')
        add('</g>')

    # 30-day activity strip
    sy, sh = 168, 50
    add(f'<text x="22" y="{sy}" class="m" font-size="10.5" fill="{P["muted"]}" letter-spacing=".8">'
        f'INDIA-RELEVANT KEV ADDITIONS · LAST {DAYS} DAYS</text>')
    add(f'<rect x="{W - 250}" y="{sy - 9}" width="9" height="9" rx="2" fill="{P["red"]}"/>'
        f'<text x="{W - 236}" y="{sy}" class="s" font-size="11" fill="{P["muted"]}">high</text>'
        f'<rect x="{W - 196}" y="{sy - 9}" width="9" height="9" rx="2" fill="{P["amber"]}"/>'
        f'<text x="{W - 182}" y="{sy}" class="s" font-size="11" fill="{P["muted"]}">medium</text>'
        f'<text x="{W - 22}" y="{sy}" text-anchor="end" class="s" font-size="11" fill="{P["muted"]}">'
        f'{sum(t for _, _, t in s["strip"])} in {DAYS}d</text>')
    peak = max([t for _, _, t in s["strip"]] + [1])
    bw = (W - 44) / DAYS
    base = sy + 14 + sh
    for n, (day, hi, tot) in enumerate(s["strip"]):
        x = 22 + n * bw
        add(f'<rect x="{x + 2:.1f}" y="{base - 2}" width="{bw - 4:.1f}" height="2" rx="1" fill="{P["line"]}"/>')
        if tot:
            th = max(6, sh * tot / peak)
            hh = th * hi / tot
            add(f'<rect x="{x + 2:.1f}" y="{base - th:.1f}" width="{bw - 4:.1f}" height="{th:.1f}" rx="2" fill="{P["amber"]}"/>')
            if hi:
                add(f'<rect x="{x + 2:.1f}" y="{base - hh:.1f}" width="{bw - 4:.1f}" height="{hh:.1f}" rx="2" fill="{P["red"]}"/>')

    # table
    hy = row_y0 - 10
    cols = [(22, "NEWEST HIGH-RELEVANCE"), (196, "PRODUCT"), (468, "ADDED"), (556, "CISA DEADLINE"), (676, "EPSS")]
    for x, label in cols:
        add(f'<text x="{x}" y="{hy}" class="m" font-size="10.5" fill="{P["muted"]}" letter-spacing=".8">{label}</text>')
    for n, i in enumerate(s["rows"]):
        y = row_y0 + n * row_h
        mid = y + row_h / 2 + 4
        add(f'<g class="in" style="animation-delay:{0.45 + n * 0.1:.2f}s">')
        add(f'<line x1="22" y1="{y}" x2="{W - 22}" y2="{y}" stroke="{P["line"]}"/>')
        add(f'<text x="22" y="{mid}" class="m" font-size="13" font-weight="600" fill="{P["green"]}">{escape(i["cve"])}</text>')
        add(f'<text x="196" y="{mid}" class="s" font-size="13.5" fill="{P["text"]}">{escape(product(i))}</text>')
        if i.get("known_ransomware"):
            add(f'<rect x="392" y="{mid - 13}" width="66" height="18" rx="9" fill="{P["orange"]}" fill-opacity=".15" stroke="{P["orange"]}" stroke-opacity=".6"/>'
                f'<text x="425" y="{mid}" text-anchor="middle" class="m" font-size="10" fill="{P["orange"]}">ransomware</text>')
        added = dt.date.fromisoformat(i["date_added"])
        add(f'<text x="468" y="{mid}" class="s" font-size="13" fill="{P["muted"]}">{added:%d %b}</text>')
        label, colour = due_chip(i, s["today"])
        add(f'<rect x="556" y="{mid - 13}" width="92" height="18" rx="9" fill="{colour}" fill-opacity=".12"/>'
            f'<text x="602" y="{mid}" text-anchor="middle" class="m" font-size="11" fill="{colour}">{label}</text>')
        e, pct = i.get("epss"), i.get("epss_percentile") or 0
        colour = epss_colour(e)
        add(f'<rect x="676" y="{mid - 8}" width="110" height="8" rx="4" fill="{P["panel"]}" stroke="{P["line"]}"/>')
        if e is not None:
            add(f'<rect x="676" y="{mid - 8}" width="{max(4, 110 * pct):.1f}" height="8" rx="4" fill="{colour}"/>')
        add(f'<text x="{W - 22}" y="{mid}" text-anchor="end" class="m" font-size="12" fill="{colour}">{epss_text(e)}</text>')
        add('</g>')
    fy = row_y0 + row_h * len(s["rows"])
    add(f'<line x1="22" y1="{fy}" x2="{W - 22}" y2="{fy}" stroke="{P["line"]}"/>')
    add(f'<text x="22" y="{fy + 24}" class="s" font-size="11" fill="{P["muted"]}">EPSS bar = percentile among all scored CVEs · '
        f'deadline = CISA remediation due date · sources: CISA KEV, FIRST EPSS</text>')
    add('</svg>')
    return "\n".join(out) + "\n"


def readme_block(s):
    links = " · ".join(f"[`{i['cve']}`]({TRACKER}/vulnerabilities?cve={i['cve']})" for i in s["rows"])
    alt = (f"India Threat Tracker: {s['week']} India-relevant flaws added to CISA KEV in the last 7 days, "
           f"{s['week_high']} high relevance, {s['total']} on the watchlist")
    return f"""{START}
<div align="center">

<a href="{TRACKER}/vulnerabilities"><img src="{SVG}" width="860" alt="{alt}" /></a>

<sub>Open: {links} · redrawn daily from the [India Threat Tracker]({TRACKER})</sub>

</div>
{END}"""


# ---------------------------------------------------------------- main

def write_if_changed(path, text):
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def main(argv):
    try:
        if "--file" in argv:
            with open(argv[argv.index("--file") + 1], encoding="utf-8") as f:
                feed = json.load(f)
        else:
            req = urllib.request.Request(FEED, headers={"User-Agent": "sohankanna-profile-readme"})
            with urllib.request.urlopen(req, timeout=60) as r:
                feed = json.load(r)
        s = summarise(feed)
        svg, block = draw(s), readme_block(s)
    except Exception as e:  # never break the profile because the feed hiccupped
        print(f"::warning::Tracker feed unavailable ({e}); nothing changed")
        return 0
    with open(README, encoding="utf-8") as f:
        text = f.read()
    if START not in text or END not in text:
        print("::error::TRACKER markers missing from README.md")
        return 1
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    changed = write_if_changed(SVG, svg) | write_if_changed(README, new)
    print("Tracker card updated" if changed else "No change")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
