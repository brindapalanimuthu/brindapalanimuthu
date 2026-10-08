"""Builds assets/activity.svg from the public GitHub contribution calendar.
No third-party service, no token. If GitHub can't be reached, the old file is kept."""
import re, sys, os, datetime as dt, urllib.request

USER = os.environ.get("GH_USER", "brindapalanimuthu")
OUT = "assets/activity.svg"
ACCENT, BG, TEXT, MUTED = "#8b7fd1", "#0d1117", "#c9d1d9", "#8b949e"

def fetch():
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions",
                                 headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode()

def parse(html):
    cells = dict(re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-\d+-\d+)"', html) and
                 [(i, d) for d, i in re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-\d+-\d+)"', html)])
    counts = {}
    for cid, text in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*([^<]+)', html):
        m = re.match(r"(\d+) contribution", text.strip())
        counts[cid] = int(m.group(1)) if m else 0
    days = sorted((dt.date.fromisoformat(d), counts.get(cid, 0)) for cid, d in cells.items())
    return days

def build(days):
    # weekly totals
    weeks, cur = [], []
    for d, c in days:
        cur.append((d, c))
        if d.weekday() == 5 or (d, c) == days[-1]:   # Saturday ends a GitHub week
            weeks.append((cur[0][0], sum(x[1] for x in cur))); cur = []
    if cur: weeks.append((cur[0][0], sum(x[1] for x in cur)))
    total = sum(c for _, c in days); peak = max(w[1] for w in weeks) or 1
    W, H, L, R, T, B = 900, 300, 50, 25, 70, 45
    pw, ph = W-L-R, H-T-B
    pts = [(L + i*pw/(len(weeks)-1), T + ph - (v/peak)*ph) for i, (_, v) in enumerate(weeks)]
    # smooth path
    path = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mx = (x0+x1)/2
        path += f" C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    area = path + f" L{pts[-1][0]:.1f},{T+ph} L{pts[0][0]:.1f},{T+ph} Z"
    grid = "".join(f'<line x1="{L}" x2="{W-R}" y1="{T+ph*k/4:.1f}" y2="{T+ph*k/4:.1f}" stroke="#21262d"/>'
                   f'<text x="{L-8}" y="{T+ph*k/4+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="11">{round(peak*(4-k)/4)}</text>'
                   for k in range(5))
    months, last = "", None
    for i, (d, _) in enumerate(weeks):
        if d.month != last and i % 1 == 0 and d.day <= 7:
            months += f'<text x="{pts[i][0]:.1f}" y="{H-18}" text-anchor="middle" fill="{MUTED}" font-size="11">{d.strftime("%b")}</text>'
            last = d.month
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{BG}" stroke="{ACCENT}" stroke-width="2"/>'
                   for (x, y), (_, v) in zip(pts, weeks) if v > 0)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient></defs>
<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>
<text x="{L}" y="32" fill="{TEXT}" font-size="17" font-weight="600">{USER}'s Contribution Graph</text>
<text x="{L}" y="52" fill="{MUTED}" font-size="12">{total} contributions in the last year · weekly totals · updated {dt.date.today():%d %b %Y}</text>
{grid}<path d="{area}" fill="url(#g)"/><path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{dots}{months}</svg>'''

if __name__ == "__main__":
    try:
        days = parse(fetch())
        if len(days) < 300: raise RuntimeError("unexpected data")
    except Exception as e:
        print("skip:", e); sys.exit(0)          # keep the previous image
    os.makedirs("assets", exist_ok=True)
    open(OUT, "w").write(build(days)); print("wrote", OUT)
