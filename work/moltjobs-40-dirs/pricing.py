"""Extract pricing with context, not the first dollar sign on the page.

A price only counts when a currency amount appears within ~120 chars of a
submission/listing/fee word, or inside the same <li>/<div>/<td> as one.
"""
import json, re
import concurrent.futures as cf
import requests

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
KEY = re.compile(r"(submi\w*|listing|get listed|fee|pricing|plan|package|review)", re.I)
AMT = re.compile(r"(?:US)?\$\s?(\d{1,4}(?:\.\d{2})?)|(\d{1,4}(?:\.\d{2})?)\s?(?:USD|usd)")
FREE_WORDS = re.compile(r"\b(free|no cost|no charge|complimentary|\$0)\b", re.I)

rows = [json.loads(l) for l in open("verify_rows.jsonl")]

def grab(g):
    if g.get("status") == 403 or not g.get("status"):
        return g["name"], [], []
    try:
        r = requests.get(g["final_url"] or g["url"],
                         headers={"User-Agent": UA}, timeout=(6, 18))
        if r.status_code >= 400:
            return g["name"], [], []
        html = r.text[:1_200_000]
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]{0,200}>", " ", text)
        text = re.sub(r"&nbsp;?|&amp;", " ", text)
        text = re.sub(r"\s+", " ", text)
        amounts, frees = [], []
        for m in AMT.finditer(text):
            s, e = m.start(), m.end()
            window = text[max(0, s - 130):e + 130]
            if KEY.search(window):
                val = m.group(1) or m.group(2)
                try:
                    fv = float(val)
                except Exception:
                    continue
                if 0 <= fv <= 5000:
                    amounts.append((fv, window.strip()[:150]))
        # pricing-word free signals near submission words
        for m in FREE_WORDS.finditer(text):
            window = text[max(0, m.start() - 90):m.end() + 90]
            if re.search(r"submi\w*|listing|get listed", window, re.I):
                frees.append(window.strip()[:140])
        return g["name"], amounts, frees
    except Exception:
        return g["name"], [], []

res = {}
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    for name, amts, frees in ex.map(grab, rows):
        # dedupe amounts, keep smallest 4 distinct
        seen, uniq = set(), []
        for v, w in sorted(amts):
            if v in seen:
                continue
            seen.add(v)
            uniq.append((v, w))
        res[name] = {"amounts": uniq[:4], "free": frees[:2]}
        print(f"{name[:26]:26} amts={[v for v,_ in uniq[:4]]} free={len(frees)}", flush=True)

json.dump(res, open("pricing_ctx.json", "w"), indent=1)
