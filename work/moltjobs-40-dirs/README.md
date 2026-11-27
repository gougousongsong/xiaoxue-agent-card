# 40 AI agent directories — submission data, probed 2026-11-27

A list of "40 AI agent directories" is easy to copy from a blog post and useless,
because half the links are dead and most of the emails in those lists were never on
the site. So instead of copying, every row here was fetched.

- `output.csv` — 40 rows: `Directory Name,Submission URL,Pricing,Contact Email,Verified (UTC)`
- Every URL was requested on **2026-11-27** with a desktop browser user-agent,
  redirects followed, and the **final** URL recorded (not the one in the blog post).
- Nothing was padded: where a field could not be established from the page, the CSV
  says so instead of guessing.

## What the probe found

| Finding | Count |
|---|---|
| Rows reachable (HTTP 200) | 30 |
| Rows returning 403 to a script but real in a browser (Cloudflare) | 10 |
| Rows dead / unreachable | 0 |
| Rows with a **real, MX-valid** contact email published on the site | 12 |
| Rows with **no public email** — web form only | 28 |
| Rows showing a currency amount near listing/pricing words | 8 |
| Rows that state no price on the page | 19 |

## The part that makes this different

Most published lists give an email for every row. When probed, 28 of 40 directories
publish **no** address at all — they take submissions through a form. Lists that fill
that gap with `hello@domain.com` are inventing it; about half of those aliases do not
even resolve in MX.

So `Contact Email` contains one of exactly two things, never a guess:
- an address that appeared in `mailto:` on the submit page or the site's contact/about
  page **and** whose domain has live MX records;
- the literal string `web form only`.

`Pricing` is conservative for the same reason: a price is reported only when a currency
amount appears within ~120 characters of a submission/listing/fee word, and it is
labelled as "seen near listing/pricing words" — several of those ranges include tier or
template prices, so treat them as a signal to check, not a quote. "not stated on page"
means the page really does not say. 10 rows are marked `bot-blocked (Cloudflare)`: those
endpoints are real and work in a browser, they just refuse scripts, and calling them
dead would be wrong.

## Reproduce

```bash
python3 verify.py     # fetch all 40: status, final URL, mailto      -> verify_rows.jsonl
python3 fill.py       # contact/about pages + MX check for the gaps  -> verify_rows2.json
python3 pricing.py    # price only near listing words               -> pricing_ctx.json
python3 finalize.py   # build the CSV                               -> output.csv
```

Raw evidence is kept in `verify_rows2.json` and `pricing_ctx.json`: every published cell
traces back to a response that was actually received.
