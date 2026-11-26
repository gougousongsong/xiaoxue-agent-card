/**
 * First-party page view for ABK's own console.
 *
 * No cookie, no generated ID, no storage: the server dedupes a visitor with a
 * salted digest of the request it already receives. This keeps the count honest
 * across reloads without tracking anyone between days or pages.
 */
(function () {
  try {
    var base = "/xiaoxue-agent-card";
    var path = location.pathname.indexOf(base) === 0
      ? location.pathname.slice(base.length) || "/"
      : location.pathname;
    var img = new Image();
    img.referrerPolicy = "no-referrer";
    img.src =
      "https://abk.gougousongsong.dpdns.org/api/v1/site-visits/p.gif" +
      "?site=xiaoxue-agent-card&path=" +
      encodeURIComponent(path);
  } catch (err) {
    /* a counting failure must never affect the page */
  }
})();
