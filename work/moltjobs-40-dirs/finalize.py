"""Final CSV: every cell backed by something we actually fetched on 2026-11-27."""
import json, csv
from urllib.parse import urlparse

rows = json.load(open("verify_rows2.json"))
ctx = json.load(open("pricing_ctx.json"))
DAY = "2026-11-27"

def clean_email(g):
    cands = list(g.get("mailtos") or []) + list(g.get("fill_mailtos") or [])
    host = (urlparse(g.get("final_url") or g["url"]).netloc or "").lower()
    root = ".".join(host.split(".")[-2:]) if host else ""
    reject = ("yourstartup", "yourcompany", "example", "yourdomain", "sentry",
              "brightdental", "hf.co", "@2x", ".png", ".jpg", "noreply", "no-reply")
    best, best_score = None, -1
    for a in cands:
        a = a.lower()
        if any(x in a for x in reject):
            continue
        d, local = a.split("@")[-1], a.split("@")[0]
        same = bool(root) and (d == root or d.endswith("." + root))
        role = local in ("hello", "support", "submit", "submissions", "contact",
                         "info", "help", "partners", "marketplace", "press")
        if not same and not role:
            continue
        score = (2 if same else 0) + (1 if role else 0)
        if score > best_score:
            best, best_score = a, score
    return best or "web form only"

def pricing(g):
    if g.get("status") == 403:
        return "bot-blocked (Cloudflare) - check in browser"
    if not g.get("status") or g["status"] >= 400:
        return "unreachable"
    c = ctx.get(g["name"], {})
    amts = [v for v, _ in c.get("amounts", [])]
    frees = c.get("free", [])
    if amts:
        lo, hi = min(amts), max(amts)
        rng = f"${lo:g}" if lo == hi else f"${lo:g}-${hi:g}"
        return f"paid, {rng} seen near listing/pricing words" + (" (+free tier text)" if frees else "")
    if frees:
        return "free/freemium stated near listing words (no price shown)"
    return "not stated on page"

out = []
for g in rows:
    out.append([g["name"], g.get("final_url") or g["url"], pricing(g),
                clean_email(g), DAY])

with open("ai-agent-directories-verified.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Directory Name", "Submission URL", "Pricing", "Contact Email", "Verified (UTC)"])
    w.writerows(out)

n_email = sum(1 for r in out if r[3] != "web form only")
n_price = sum(1 for r in out if r[2].startswith("paid"))
print(f"rows={len(out)} emails={n_email} paid_signals={n_price} "
      f"blocked={sum(1 for r in out if 'bot-blocked' in r[2])} "
      f"no_price={sum(1 for r in out if r[2].startswith('not stated'))}")
for r in out:
    print(f"| {r[0][:26]:26} | {r[2][:44]:44} | {r[3]}")
