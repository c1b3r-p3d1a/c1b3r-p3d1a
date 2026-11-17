"""Regenerate assets/card-*.svg from live GitHub data. Run on a schedule by .github/workflows/cards.yml."""
import base64
import datetime as dt
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
    # PRs by other people where I left comments (testing, reporting errors)
    helped = api(f"search/issues?q=repo:{UPSTREAM}+is:pr+commenter:{USER}+-author:{USER}&per_page=1")["total_count"]
    return commits, len(prs), merged, helped, top


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


def card(t, kicker, title, desc, body, lang, lcolor, note, tag=None):
    vw, vh = W + 2 * PAD, H + 2 * PAD
    pill = ""
    if tag:  # small pill right after the title, e.g. "AI" for mostly AI-generated work
        x = 28 + 15.7 * len(title) + 12
        w = 16 + 7.3 * len(tag)
        pill = (f'<rect x="{x:.0f}" y="55" width="{w:.0f}" height="22" rx="11" fill="{t["chip"]}" stroke="{t["bd"]}"/>'
                f'<text x="{x + w / 2:.0f}" y="70" text-anchor="middle" style="{F};font-size:11px" fill="{t["mu"]}">{tag}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}" height="{vh:.2f}" viewBox="{-PAD:.2f} {-PAD:.2f} {vw:.2f} {vh:.2f}">
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["bd"]}"/>
<text x="28" y="40" style="{F};font-size:11px;letter-spacing:2px" fill="{t["ac"]}">{kicker}</text>
<text x="28" y="74" style="{F};font-size:26px;font-weight:700" fill="{t["fg"]}">{title}</text>{pill}
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
        x = 28 + i * 108
        out += (f'<text x="{x}" y="138" style="{F};font-size:26px;font-weight:700" fill="{t["fg"]}">{n}</text>'
                f'<text x="{x}" y="156" style="{S};font-size:12px" fill="{t["mu"]}">{label}</text>')
    return out + chips(libs, 28, 168, t)


def main():
    lines = emu_lines()
    commits, prs, merged, helped, libs = anyps5()
    print(f"riscv-emu: {lines} lines | AnyPS5: {commits} commits, {prs} PRs, {merged} merged, {helped} helped, libs={libs}")
    ms = emu_milestones()
    print("milestones:", ", ".join(f"{n}={d}" for n, d in ms))
    cards = {}
    for name, t in THEMES.items():
        cards[f"riscv-{name}"] = card(t, "BUILDING", "riscv-emu", "A RISC-V emulator, written from the spec.",
                                      pipeline(t), "C", "#555555", f"{short(lines)} lines of C")
        cards[f"anyps5-{name}"] = card(t, "CONTRIBUTING", "AnyPS5", "Reimplementing PS5 system libraries.",
                                       stats(t, [(short(commits), "commits"), (short(prs), "PRs opened"), (short(merged), "merged"), (short(helped), "PRs helped")], libs),
                                       "C++", "#f34b7d", UPSTREAM, tag="AI")
        cards[f"timeline-{name}"] = timeline(t, dt.date.today(), ms)
    write_versioned(cards)


# ---- roadmap ---------------------------------------------------------------
def emu_milestones():
    """[(name, date|None)] from roadmap/milestones.json: a milestone is done on the first riscv-emu commit
    whose src/ + include/ match all its 'detect' regexes (and HEAD still matches), or on its manual 'done' date."""
    import subprocess, tempfile
    spec = json.load(open("roadmap/milestones.json", encoding="utf-8"))["milestones"]
    repo = tempfile.mkdtemp()
    # skip big blobs (kernel image, rootfs): only small source files are needed
    subprocess.run(["git", "clone", "-q", "--filter=blob:limit=512k", f"https://github.com/{EMU}.git", repo], check=True)

    def git(*a):
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=True).stdout

    commits = [l.split() for l in git("log", "--reverse", "--format=%H %ad", "--date=short").splitlines()]
    src = {}
    for sha, _ in commits:
        files = [f for f in git("ls-tree", "-r", "--name-only", sha).splitlines() if re.match(r"(src|include)/.*\.[ch]$", f)]
        src[sha] = "\n".join(git("show", f"{sha}:{f}") for f in files)
    out = []
    for m in spec:
        when = m.get("done")
        if "detect" in m:
            ok = lambda sha: all(re.search(p, src[sha]) for p in m["detect"])
            if ok(commits[-1][0]):
                when = next(d for sha, d in commits if ok(sha))
        out.append((m["name"], dt.date.fromisoformat(when) if when else None))
    return out
TL_START, TL_MONTHS = (2026, 7), 30          # Jul 2026 .. Dec 2028
EMU_START, EMU_END = (2026, 7), (2028, 1)    # riscv-emu: first commit .. target "done by end of 2027"
OS_START = (2028, 1)                         # OS from scratch: after the emulator, end date not set


def months_since(ym, d):
    return (d[0] - ym[0]) * 12 + d[1] - ym[1]


assert months_since((2026, 7), (2028, 1)) == 18


def timeline(t, today, milestones):
    cols, row_h = 4, 24
    rows = -(-len(milestones) // cols)
    list_y = 236
    TW, TH = 980, list_y + (rows - 1) * row_h + 30
    bar_bottom = 192  # tracks + NOW label live above this; milestone list below
    pad = 6 / 1292 * TW / (1 - 2 * 6 / 1292)  # same outer gap as the stack strip
    x0, x1 = 196, TW - 28
    step = (x1 - x0) / TL_MONTHS

    def mx(ym, frac=0.0):
        return x0 + (months_since(TL_START, ym) + frac) * step

    out = ""
    for i in range(TL_MONTHS):  # month initials, year labels and year dividers
        y, m = TL_START[0] + (TL_START[1] - 1 + i) // 12, (TL_START[1] - 1 + i) % 12 + 1
        x = x0 + i * step
        if m == 1 or i == 0:
            out += f'<text x="{x + 2:.1f}" y="66" style="{F};font-size:12px;font-weight:700" fill="{t["fg"]}">{y}</text>'
            if i:
                out += f'<line x1="{x:.1f}" y1="54" x2="{x:.1f}" y2="{bar_bottom - 20}" stroke="{t["bd"]}"/>'
        out += f'<text x="{x + step / 2:.1f}" y="86" text-anchor="middle" style="{F};font-size:10px" fill="{t["mu"]}">{"JFMAMJJASOND"[m - 1]}</text>'

    now = mx((today.year, today.month), (today.day - 1) / 31)
    ey, oy = 118, 158  # track centre lines
    e0, e1 = mx(EMU_START), mx(EMU_END)
    done = min(max(now, e0), e1)
    o0 = mx(OS_START)
    n_done = sum(1 for _, d in milestones if d)
    out += f'''
<text x="28" y="{ey + 1}" style="{F};font-size:14px;font-weight:700" fill="{t["fg"]}">riscv-emu</text>
<text x="28" y="{ey + 17}" style="{S};font-size:11px" fill="{t["mu"]}">{n_done}/{len(milestones)} milestones</text>
<rect x="{e0:.1f}" y="{ey - 7}" width="{e1 - e0:.1f}" height="14" rx="7" fill="{t["chip"]}" stroke="{t["bd"]}"/>
<rect x="{e0:.1f}" y="{ey - 7}" width="{done - e0:.1f}" height="14" rx="7" fill="{t["ac"]}"/>
<path d="M{e1:.1f} {ey - 7}l7 7-7 7-7-7z" fill="{t["bg"]}" stroke="{t["ac"]}" stroke-width="1.5"/>
<text x="{e1 + 14:.1f}" y="{ey + 4}" style="{S};font-size:12px" fill="{t["mu"]}">fully working · end of 2027</text>
<text x="28" y="{oy + 5}" style="{F};font-size:14px;font-weight:700" fill="{t["fg"]}">OS from scratch</text>
<rect x="{o0:.1f}" y="{oy - 7}" width="{x1 - o0:.1f}" height="14" rx="7" fill="url(#fade)" stroke="{t["bd"]}" stroke-dasharray="4 4"/>
<text x="{o0 - 10:.1f}" y="{oy + 4}" text-anchor="end" style="{S};font-size:12px" fill="{t["mu"]}">runs on riscv-emu · date not set</text>
<line x1="{now:.1f}" y1="96" x2="{now:.1f}" y2="{bar_bottom - 20}" stroke="{t["ac"]}" stroke-width="1.5"/>
<text x="{now:.1f}" y="{bar_bottom - 8}" text-anchor="middle" style="{F};font-size:10px;letter-spacing:1px" fill="{t["ac"]}">NOW</text>'''

    # milestone markers on the riscv-emu bar: done = tick at its date, pending = hollow dots spread from now to the target
    pending = [i for i, (_, d) in enumerate(milestones) if not d]
    # done milestones days apart would overlap: one circle per month, mid-month, showing how many were done in it
    per_month = {}
    for _, d in milestones:
        if d:
            per_month[(d.year, d.month)] = per_month.get((d.year, d.month), 0) + 1
    for ym, n in sorted(per_month.items()):
        x = mx(ym, 0.5)
        out += (f'<circle cx="{x:.1f}" cy="{ey}" r="7" fill="{t["bg"]}" stroke="{t["ac"]}" stroke-width="1.5"/>'
                f'<text x="{x:.1f}" y="{ey + 3.5}" text-anchor="middle" style="{F};font-size:9px;font-weight:700" fill="{t["ac"]}">{n}</text>')
    for k, _ in enumerate(pending):
        x = done + 14 + (e1 - 20 - done - 14) * (k + 1) / (len(pending) + 1)
        out += f'<circle cx="{x:.1f}" cy="{ey}" r="4.5" fill="{t["bg"]}" stroke="{t["mu"]}" stroke-width="1.5"/>'

    # milestone list, column-major, numbered in build order
    out += f'<line x1="28" y1="{list_y - 26}" x2="{TW - 28}" y2="{list_y - 26}" stroke="{t["bd"]}"/>'
    colw = (TW - 56) / cols
    for i, (name, d) in enumerate(milestones):
        x, y = 28 + (i // rows) * colw, list_y + (i % rows) * row_h
        dot = (f'<circle cx="{x + 5}" cy="{y - 4}" r="4.5" fill="{t["ac"]}"/>' if d else
               f'<circle cx="{x + 5}" cy="{y - 4}" r="4" fill="none" stroke="{t["mu"]}" stroke-width="1.2"/>')
        when = f'<tspan fill="{t["mu"]}" style="{F};font-size:10px">  {d.strftime("%b %Y")}</tspan>' if d else ""
        out += (dot + f'<text x="{x + 18}" y="{y}" style="{S};font-size:12px" fill="{t["fg"] if d else t["mu"]}">'
                f'{name}{when}</text>')
    vw, vh = TW + 2 * pad, TH + 2 * pad
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{vw:.2f}" height="{vh:.2f}" viewBox="{-pad:.2f} {-pad:.2f} {vw:.2f} {vh:.2f}">
<defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{t["ac"]}" stop-opacity=".25"/><stop offset="1" stop-color="{t["ac"]}" stop-opacity="0"/></linearGradient></defs>
<rect x=".5" y=".5" width="{TW - 1}" height="{TH - 1}" rx="10" fill="{t["bg"]}" stroke="{t["bd"]}"/>
<text x="28" y="40" style="{F};font-size:11px;letter-spacing:2px" fill="{t["ac"]}">ROADMAP</text>
{out}
</svg>
'''


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
