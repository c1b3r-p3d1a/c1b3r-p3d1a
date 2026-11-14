"""Regenerate assets/card-*.svg from live GitHub data. Run daily by .github/workflows/cards.yml."""
import base64
import json
import os
import re
import urllib.request

USER = "c1b3r-p3d1a"
EMU = f"{USER}/riscv-emu"
UPSTREAM = "boykopovar/AnyPS5"


def api(path):
    req = urllib.request.Request("https://api.github.com/" + path, headers={
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json",
    })
    return json.load(urllib.request.urlopen(req))


def short(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


assert short(38) == "38" and short(1200) == "1.2k" and short(1000) == "1k" and short(12345) == "12.3k"


def emu_lines():
    tree = api(f"repos/{EMU}/git/trees/HEAD?recursive=1")["tree"]
    total = 0
    for f in tree:
        if f["type"] == "blob" and f["path"].endswith((".c", ".h")):
            total += base64.b64decode(api(f"repos/{EMU}/git/blobs/{f['sha']}")["content"]).count(b"\n")
    return total


def anyps5():
    prs, page = [], 1
    while True:
        items = api(f"search/issues?q=repo:{UPSTREAM}+author:{USER}+is:pr&per_page=100&page={page}")["items"]
        prs += items
        if len(items) < 100:
            break
        page += 1
    commits = merged = 0
    libs = {}
    for pr in prs:
        d = api(f"repos/{UPSTREAM}/pulls/{pr['number']}")
        commits += d["commits"]
        if d["merged"]:
            merged += 1
            m = re.match(r"\w+\((lib\w+)\)", d["title"])
            if m:
                libs[m[1]] = libs.get(m[1], 0) + 1
    top = sorted(libs, key=libs.get, reverse=True)[:2]
    return commits, len(prs), merged, top


# ---- drawing -------------------------------------------------------------
W, H = 480, 240
PAD = 2 * 6 / 1292 * W / (1 - 4 * 6 / 1292)  # same outer gap as the banner and stack strip
F = "font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
S = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
THEMES = dict(
    dark=dict(bg="#0d1117", bd="#30363d", fg="#e6edf3", mu="#8b949e", chip="#161b22", ac="#3fb950"),
    light=dict(bg="#ffffff", bd="#d1d9e0", fg="#1f2328", mu="#59636e", chip="#f6f8fa", ac="#1a7f37"),
)


def chips(items, x, y, t):
    out = ""
    for it in items:
        w = 16 + 7.3 * len(it)
        out += (f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="22" rx="11" fill="{t["chip"]}" stroke="{t["bd"]}"/>'
                f'<text x="{x + w / 2:.0f}" y="{y + 15}" text-anchor="middle" style="{F};font-size:11px" fill="{t["mu"]}">{it}</text>')
        x += w + 8
    return out


def card(t, kicker, title, desc, body, lang, lcolor, note):
    vw, vh = W + 2 * PAD, H + 2 * PAD
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}" height="{vh:.2f}" viewBox="{-PAD:.2f} {-PAD:.2f} {vw:.2f} {vh:.2f}">
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["bd"]}"/>
<text x="28" y="40" style="{F};font-size:11px;letter-spacing:2px" fill="{t["ac"]}">{kicker}</text>
<text x="28" y="74" style="{F};font-size:26px;font-weight:700" fill="{t["fg"]}">{title}</text>
<text x="28" y="100" style="{S};font-size:14px" fill="{t["mu"]}">{desc}</text>
{body}
<line x1="28" y1="200" x2="{W - 28}" y2="200" stroke="{t["bd"]}"/>
<circle cx="33" cy="218" r="5" fill="{lcolor}"/>
<text x="45" y="222" style="{S};font-size:12px" fill="{t["mu"]}">{lang}</text>
<text x="{W - 28}" y="222" text-anchor="end" style="{S};font-size:12px" fill="{t["mu"]}">{note}</text>
</svg>
'''


def pipeline(t):
    out, x = "", 28
    for i, s in enumerate(["fetch", "decode", "execute", "commit"]):
        hl = i == 2
        out += (f'<rect x="{x}" y="120" width="84" height="30" rx="6" fill="{t["chip"]}" stroke="{t["ac"] if hl else t["bd"]}"/>'
                f'<text x="{x + 42}" y="139" text-anchor="middle" style="{F};font-size:12px" fill="{t["fg"] if hl else t["mu"]}">{s}</text>')
        if i < 3:
            out += f'<path d="M{x + 88} 135h10m-4-4 4 4-4 4" fill="none" stroke="{t["mu"]}" stroke-width="1.3"/>'
        x += 102
    return out + chips(["RV32IMA", "Zicsr", "Sv32", "M/S/U modes"], 28, 164, t)


def stats(t, nums, libs):
    out = ""
    for i, (n, label) in enumerate(nums):
        x = 28 + i * 140
        out += (f'<text x="{x}" y="143" style="{F};font-size:28px;font-weight:700" fill="{t["fg"]}">{n}</text>'
                f'<text x="{x + 8 + 17 * len(n)}" y="142" style="{S};font-size:13px" fill="{t["mu"]}">{label}</text>')
    return out + chips(libs, 28, 164, t)


def main():
    lines = emu_lines()
    commits, prs, merged, libs = anyps5()
    print(f"riscv-emu: {lines} lines | AnyPS5: {commits} commits, {prs} PRs, {merged} merged, libs={libs}")
    cards = {}
    for name, t in THEMES.items():
        cards[f"riscv-{name}"] = card(t, "BUILDING", "riscv-emu", "A RISC-V emulator, written from the spec.",
                                      pipeline(t), "C", "#555555", f"{short(lines)} lines of C")
        cards[f"anyps5-{name}"] = card(t, "CONTRIBUTING", "AnyPS5", "Reimplementing PS5 system libraries.",
                                       stats(t, [(short(commits), "commits"), (short(prs), "pull requests"), (short(merged), "merged")], libs),
                                       "C++", "#f34b7d", UPSTREAM)
    write_versioned(cards)


def write_versioned(cards):
    """Save each card as assets/cards/<key>-<content hash>.svg and point README at it.
    GitHub's raw CDN caches by path (query strings are dropped on redirect), so a new name is the only reliable refresh."""
    import glob, hashlib
    os.makedirs("assets/cards", exist_ok=True)
    keep = set()
    readme = open("README.md", encoding="utf-8").read()
    for key, svg in cards.items():
        path = f"assets/cards/{key}-{hashlib.sha1(svg.encode()).hexdigest()[:8]}.svg"
        keep.add(path)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        # matches both the new versioned names and the old assets/card-<key>.svg(?v=..) form
        readme = re.sub(rf"assets/(?:cards/{key}-\w+|card-{key})\.svg(?:\?v=\w+)?", path, readme)
    open("README.md", "w", encoding="utf-8", newline="\n").write(readme)
    for old in glob.glob("assets/cards/*.svg") + glob.glob("assets/card-*.svg"):
        if old.replace("\\", "/") not in keep:
            os.remove(old)


if __name__ == "__main__":
    main()
