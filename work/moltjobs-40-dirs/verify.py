"""Verify the 40-row AI-agent directory CSV, incrementally and with hard timeouts.

Writes results incrementally to verify_rows.jsonl so nothing is lost if one
host hangs. Each row: HTTP status, final URL, real mailto addresses seen in
href, whether the page has a <form>, pricing words actually present.
"""
import csv, json, re, os
import concurrent.futures as cf
import requests
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]{2,64}@[A-Za-z0-9.\-]{2,64}\.[A-Za-z]{2,6}")
OUT = "verify_rows.jsonl"

def probe(row):
    name, url, guess_price, guess_email = row
    out = {"name": name, "url": url, "guess_price": guess_price,
           "guess_email": guess_email, "status": None, "final_url": None,
           "title": "", "mailtos": [], "has_form": False,
           "price_hits": [], "error": None}
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
                         timeout=(6, 20), allow_redirects=True, stream=True)
        out["status"] = r.status_code
        out["final_url"] = r.url
        # cap body at 1.5MB to avoid pathological pages
        body = r.raw.read(1_500_000, decode_content=True) or b""
        html = body.decode(r.encoding or "utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            out["title"] = re.sub(r"\s+", " ", m.group(1)).strip()[:120]
        for mm in re.finditer(r'href=["\']mailto:([^"\'?>]+)', html, re.I):
            a = mm.group(1).strip().lower()
            if a not in out["mailtos"]:
                out["mailtos"].append(a)
        if not out["mailtos"]:
            for a in EMAIL_RE.findall(html)[:50]:
                a = a.lower()
                if any(x in a for x in ("sentry", "example.com", "wixpress", "@2x", ".png", ".jpg")):
                    continue
                out["mailtos"].append(a)
                if len(out["mailtos"]) >= 3:
                    break
        out["has_form"] = "<form" in html.lower()
        text = re.sub(r"<[^>]{0,200}>", " ", html)
        low = text.lower()
        for kw, label in [("free listing", "free"), ("100% free", "free"),
                          ("submit your tool for free", "free"),
                          ("freemium", "freemium"), ("free tier", "freemium"),
                          ("paid listing", "paid"), ("premium listing", "paid"),
                          ("per listing", "paid")]:
            if kw in low and label not in out["price_hits"]:
                out["price_hits"].append(label)
        for m2 in re.finditer(r"\$\s?\d{1,4}(?:\.\d{2})?", text):
            if "paid" not in out["price_hits"]:
                out["price_hits"].append("paid")
            out["price_example"] = m2.group(0)
            break
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return out

def main():
    rows = list(csv.reader(open("output.csv")))[1:]
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                done.add(json.loads(line)["name"])
            except Exception:
                pass
    todo = [r for r in rows if r[0] not in done]
    print(f"{len(rows)} rows, {len(done)} already done, {len(todo)} to probe", flush=True)
    fh = open(OUT, "a")
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(probe, r): r[0] for r in todo}
        for i, fut in enumerate(cf.as_completed(futs, timeout=280), 1):
            try:
                g = fut.result(timeout=1)
            except Exception as e:
                g = {"name": futs[fut], "error": f"future:{type(e).__name__}", "status": None,
                     "url": "", "final_url": None, "mailtos": [], "price_hits": [],
                     "has_form": False, "title": ""}
            fh.write(json.dumps(g) + "\n")
            fh.flush()
            print(f"[{i}/{len(todo)}] {g['name'][:28]:28} {g['status']} mail={len(g['mailtos'])} "
                  f"{'ERR:' + str(g.get('error'))[:40] if g.get('error') else ''}", flush=True)
    fh.close()

if __name__ == "__main__":
    main()
