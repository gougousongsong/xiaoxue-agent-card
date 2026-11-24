#!/usr/bin/env python3
"""Gumroad sales API -> clean CSV rows (the transform half of a Gumroad->Airtable workflow).

Usage (real):  GUMROAD_TOKEN=xxx python3 gumroad_sales_to_csv.py --live > sales.csv
Usage (demo):  python3 gumroad_sales_to_csv.py --fixture sample_gumroad_response.json > sample_sales.csv

Mapping contract (what the Airtable/Sheets columns expect):
  sale_id, created_at_utc, product_name, product_id, price_cents, price_usd, currency,
  buyer_email, buyer_name, country, refunded, license_key, utm_source, is_recurring
"""
import csv, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

FIELDS = ["sale_id","created_at_utc","product_name","product_id","price_cents","price_usd",
          "currency","buyer_email","buyer_name","country","refunded","license_key",
          "utm_source","is_recurring"]

def fetch_live(token, after=None):
    q = {"access_token": token}
    if after: q["after"] = after
    url = "https://api.gumroad.com/v2/sales?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())

def transform(payload):
    rows, seen = [], set()
    for s in payload.get("sales", []):
        sid = s.get("id")
        if not sid or sid in seen:          # idempotency: Airtable upsert key is sale_id
            continue
        seen.add(sid)
        price = s.get("price") or 0          # Gumroad returns integer cents
        ts = s.get("created_at")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
            created = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            created = ts or ""
        rows.append({
            "sale_id": sid,
            "created_at_utc": created,
            "product_name": (s.get("product_name") or "").strip(),
            "product_id": s.get("product_id") or "",
            "price_cents": price,
            "price_usd": f"{price/100:.2f}",
            "currency": s.get("currency") or "usd",
            "buyer_email": (s.get("email") or "").strip().lower(),
            "buyer_name": (s.get("full_name") or s.get("name") or "").strip(),
            "country": (s.get("country") or "").strip().upper(),
            "refunded": str(bool(s.get("refunded"))).lower(),
            "license_key": s.get("license_key") or "",
            "utm_source": ((s.get("utm_link") or {}).get("utm_source") or s.get("referrer") or "").strip(),
            "is_recurring": str(bool(s.get("subscription_id"))).lower(),
        })
    rows.sort(key=lambda r: r["created_at_utc"], reverse=True)
    return rows

def main():
    if "--live" in sys.argv:
        tok = os.environ.get("GUMROAD_TOKEN")
        if not tok:
            sys.exit("GUMROAD_TOKEN missing")
        payload = fetch_live(tok)
    else:
        path = sys.argv[sys.argv.index("--fixture")+1] if "--fixture" in sys.argv else "sample_gumroad_response.json"
        payload = json.load(open(path))
    rows = transform(payload)
    w = csv.DictWriter(sys.stdout, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    print(f"# rows={len(rows)} total_cents={sum(r['price_cents'] for r in rows)}", file=sys.stderr)

if __name__ == "__main__":
    main()
