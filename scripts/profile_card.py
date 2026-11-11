#!/usr/bin/env python3
"""Draw the profile card (assets/profile-card.svg) for the profile README.

Edit PROFILE below and re-run:

    python scripts/profile_card.py

Everything on the card comes from PROFILE; layout adapts to the text
(chips wrap onto new lines and the card grows to fit).
"""
import base64
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "profile-card.svg"

PROFILE = {
    "handle": "sohankanna",
    "base": "Bengaluru, IN",
    "now": {"role": "AI Builder Intern", "org": "Razorpay", "logo": "assets/logos/razorpay.png"},
    "heading_to": "security engineering",
    "ctf_team": "Diamond_Dogs",
    "focus": ["malware analysis", "reverse engineering", "detection engineering", "AppSec"],
    "ask_me_about": ["Ghidra", "malware triage", "SIEM pipelines", "AI agents for vuln hunting", "CTFs"],
    # (big number, label, colour key)
    "stats": [
        ("8", "DISCLOSURES ACKNOWLEDGED", "green"),
        ("TOP 1%", "CLOUDSEK CTF 2025", "purple"),
        ("22", "CTF WRITEUPS", "blue"),
        ("6,000+", "READS ON ONE WRITE-UP", "orange"),
    ],
}

P = {
    "bg": "#0d1117", "panel": "#161b22", "line": "#30363d", "text": "#e6edf3",
    "muted": "#8b949e", "green": "#00ff41", "red": "#f85149", "amber": "#d29922",
    "orange": "#f0883e", "blue": "#58a6ff", "purple": "#bc8cff", "teal": "#39d0d8",
}
FOCUS_COLOURS = ["green", "purple", "blue", "orange", "teal", "amber"]
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

W = 860
LEFT_X, LEFT_W = 22, 816
CHIP_FONT, CHIP_H, CHIP_GAP = 11.5, 24, 8


def chip_w(text):
    return len(text) * CHIP_FONT * 0.62 + 22


def chips(items, x0, y0, colours=None):
    """Lay out pills left to right, wrapping at LEFT_W. Returns (svg, bottom y)."""
    out, x, y = [], x0, y0
    for n, text in enumerate(items):
        w = chip_w(text)
        if x + w > x0 + LEFT_W:
            x, y = x0, y + CHIP_H + CHIP_GAP
        c = P[colours[n % len(colours)]] if colours else P["muted"]
        fill = f'fill="{c}" fill-opacity=".12"' if colours else f'fill="{P["panel"]}"'
        stroke = c if colours else P["line"]
        tc = c if colours else P["text"]
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{CHIP_H}" rx="{CHIP_H / 2}" {fill} '
                   f'stroke="{stroke}" stroke-opacity="{.55 if colours else 1}"/>'
                   f'<text x="{x + w / 2:.1f}" y="{y + 16}" text-anchor="middle" class="m" '
                   f'font-size="{CHIP_FONT}" fill="{tc}">{escape(text)}</text>')
        x += w + CHIP_GAP
    return "".join(out), y + CHIP_H


def label(x, y, text):
    return (f'<text x="{x}" y="{y}" class="m" font-size="10.5" fill="{P["muted"]}" '
            f'letter-spacing=".8">{escape(text)}</text>')


def logo_data(path):
    data = (ROOT / path).read_bytes()
    kind = "svg+xml" if path.endswith(".svg") else "png"
    return f"data:image/{kind};base64,{base64.b64encode(data).decode()}"


def draw(p):
    body = []
    add = body.append
    top = 72

    # now: logo + role
    add(f'<clipPath id="lc"><rect x="{LEFT_X}" y="{top}" width="48" height="48" rx="10"/></clipPath>')
    add(f'<image href="{logo_data(p["now"]["logo"])}" x="{LEFT_X}" y="{top}" width="48" height="48" clip-path="url(#lc)"/>')
    add(f'<rect x="{LEFT_X}" y="{top}" width="48" height="48" rx="10" fill="none" stroke="{P["line"]}"/>')
    add(label(LEFT_X + 64, top + 14, "NOW"))
    add(f'<text x="{LEFT_X + 64}" y="{top + 40}" class="s" font-size="19" font-weight="700" fill="{P["text"]}">'
        f'{escape(p["now"]["role"])} <tspan fill="{P["muted"]}" font-weight="400">@</tspan> '
        f'<tspan fill="{P["blue"]}">{escape(p["now"]["org"])}</tspan></text>')

    # heading to / ctf team, right of the role
    for x, key, icon, colour in [(470, "heading_to", "→", "green"), (680, "ctf_team", "⚑", "red")]:
        add(label(x, top + 14, key.replace("_", " ").upper()))
        add(f'<text x="{x}" y="{top + 40}" class="s" font-size="15" fill="{P["text"]}">'
            f'<tspan fill="{P[colour]}" class="m">{icon} </tspan>{escape(p[key])}</text>')

    # focus chips
    y = top + 82
    add(label(LEFT_X, y, "FOCUS"))
    svg, bottom = chips(p["focus"], LEFT_X, y + 10, FOCUS_COLOURS)
    add(svg)

    # ask me about
    y = bottom + 26
    add(label(LEFT_X, y, "ASK ME ABOUT"))
    svg, bottom = chips(p["ask_me_about"], LEFT_X, y + 10)
    add(svg)

    # stat tiles across the bottom
    y = bottom + 22
    n_t = len(p["stats"])
    tw = (W - 44 - 12 * (n_t - 1)) / n_t
    for n, (big, text, colour) in enumerate(p["stats"]):
        x = LEFT_X + n * (tw + 12)
        c = P[colour]
        add(f'<g class="in" style="animation-delay:{0.15 + n * 0.08:.2f}s">'
            f'<rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="74" rx="8" fill="{P["panel"]}" stroke="{P["line"]}"/>'
            f'<rect x="{x:.1f}" y="{y + 14}" width="3" height="46" rx="1.5" fill="{c}"/>'
            f'<text x="{x + 16:.1f}" y="{y + 26}" class="m" font-size="10.5" fill="{P["muted"]}" letter-spacing=".8">{escape(text)}</text>'
            f'<text x="{x + 16:.1f}" y="{y + 60}" class="s" font-size="28" font-weight="700" fill="{c}">{escape(big)}</text>'
            f'</g>')
    left_bottom = y + 74

    H = int(left_bottom + 24)
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{escape(p["now"]["role"])} at {escape(p["now"]["org"])}; heading to {escape(p["heading_to"])}; '
        f'focus: {escape(", ".join(p["focus"]))}">',
        f"""<style>
.m{{font-family:{MONO}}} .s{{font-family:{SANS}}}
.pulse{{animation:p 2s ease-in-out infinite}} @keyframes p{{50%{{opacity:.25}}}}
.in{{opacity:0;animation:f .5s ease-out forwards}} @keyframes f{{to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.pulse,.in{{animation:none;opacity:1}}}}
</style>""",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{P["bg"]}" stroke="{P["line"]}"/>',
        f'<circle class="pulse" cx="26" cy="27" r="5" fill="{P["green"]}"/>',
        f'<text x="40" y="32" class="m" font-size="13" font-weight="700" fill="{P["green"]}" letter-spacing="1.5">OPERATOR PROFILE</text>',
        f'<text x="{W - 22}" y="32" text-anchor="end" class="m" font-size="12" fill="{P["muted"]}">'
        f'{escape(p["handle"])} · {escape(p["base"])}</text>',
        f'<line x1="1" y1="52" x2="{W - 1}" y2="52" stroke="{P["line"]}"/>',
    ]
    return "\n".join(head + body + ["</svg>"]) + "\n"


if __name__ == "__main__":
    OUT.write_text(draw(PROFILE), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
