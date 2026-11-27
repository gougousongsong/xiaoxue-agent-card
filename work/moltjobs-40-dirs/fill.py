"""Fill the gaps: for rows that were 403/blocked or had no email on the submit
page, try the site's contact/about page and check whether the mail domain can
actually receive mail (MX lookup). Only what we observe gets written down.
"""
import json, re, subprocess
import concurrent.futures as cf
import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]{2,64}@[A-Za-z0-9.\-]{2,64}\.[A-Za-z]{2,6}")
CAND = ["/contact", "/about", "/submit", "/contact-us", "/pricing"]

rows = [json.loads(l) for l in open("verify_rows.jsonl")]
need = [g for g in rows if not g.get("mailtos")]

def mx_ok(addr):
    dom = addr.split("@")[-1]
    try:
        out = subprocess.run(["dig", "+short", "MX", dom], capture_output=True, text=True, timeout=8).stdout
        return bool(out.strip())
    except Exception:
        return None

def dig_email(g):
    from urllib.parse import urlparse
    base = urlparse(g.get("final_url") or g["url"])
    root = f"{base.scheme}://{base.netloc}"
    found = []
    for p in CAND:
        try:
            r = requests.get(root + p, headers={"User-Agent": UA}, timeout=(5, 12))
            if r.status_code >= 400:
                continue
            html = r.text[:800_000]
            for m in re.finditer(r'href=["\']mailto:([^"\'?>]+)', html, re.I):
                a = m.group(1).strip().lower()
                if a not in found:
                    found.append(a)
            if not found:
                for a in EMAIL_RE.findall(html)[:40]:
                    a = a.lower()
                    if any(x in a for x in ("sentry", "example.com", "wixpress", "@2x", ".png", ".jpg", "sentry.io")):
                        continue
                    if a not in found:
                        found.append(a)
            if found:
                break
        except Exception:
            continue
    return g["name"], found

with cf.ThreadPoolExecutor(max_workers=8) as ex:
    res = {}
    for name, found in ex.map(dig_email, need):
        res[name] = found
        print(f"{name[:30]:30} -> {found[:2]}", flush=True)

# validate MX for every email we plan to publish
print("\n--- MX check ---")
for g in rows:
    addrs = g.get("mailtos") or res.get(g["name"], [])
    g["fill_mailtos"] = res.get(g["name"], [])
    best = None
    for a in addrs:
        if mx_ok(a) is True:
            best = a
            break
    g["email_verified"] = best
    print(f"{g['name'][:28]:28} {best or '-'}")

json.dump(rows, open("verify_rows2.json", "w"), indent=1)
print("\nsaved verify_rows2.json")
