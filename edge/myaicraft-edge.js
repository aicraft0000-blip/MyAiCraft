// myaicraft-edge: the Cloudflare Worker in front of myaicraft.uk.
// It upgrades http to https, redirects a few old addresses, hides retired
// files, adds security headers, and shows the site's own 404.html for
// missing pages. robots.txt and sitemap.xml come from the uploaded files.

const REDIRECTS = {
  "/astrologer.html": "/AICQindex.html", // orphan Quesi page
  "/privacy": "/privacy.html",            // extensionless links in older pages
  "/terms": "/terms.html",
  "/Gplans.html": "/grief/Gplans.html",   // root-level duplicates of the grief pages
  "/Gchat.html": "/grief/Gchat.html",
  "/Gaccount.html": "/grief/Gaccount.html",
};

const GONE = new Set([
  "/Default.html",
  "/grief/index.OLD.html",
  "/quesi-welcome-email-preview.html",
  "/river-worker.js",
  "/landing-v2.html",
  "/myaicraft-upload-2026-07-07.zip",
  "/README.md",
]);

const FALLBACK_404 = "<!doctype html><title>Page not found</title><p>That page isn't here. <a href=\"/\">Back to the start</a>.</p>";

async function notFound(origin) {
  try {
    const page = await fetch(origin + "/404.html");
    if (page.ok) {
      return new Response(page.body, {
        status: 404,
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }
  } catch (e) {}
  return new Response(FALLBACK_404, {
    status: 404,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

export default {
  async fetch(request) {
    try {
      const url = new URL(request.url);
      if (url.protocol === "http:") {
        url.protocol = "https:";
        return Response.redirect(url.toString(), 301);
      }
      const path = url.pathname;
      if (REDIRECTS[path]) {
        return Response.redirect(url.origin + REDIRECTS[path] + url.search, 301);
      }
      if (url.hostname !== "myaicraft.uk" && url.hostname !== "www.myaicraft.uk") {
        url.hostname = "myaicraft.uk";
        request = new Request(url.toString(), request);
      }
      if (GONE.has(path)) {
        return notFound(url.origin);
      }
      const origin = await fetch(request);
      if (origin.status === 404 && (request.headers.get("Accept") || "").includes("text/html")) {
        return notFound(url.origin);
      }
      const resp = new Response(origin.body, origin);
      resp.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
      resp.headers.set("X-Content-Type-Options", "nosniff");
      resp.headers.set("X-Frame-Options", "SAMEORIGIN");
      resp.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
      return resp;
    } catch (e) {
      return fetch(request);
    }
  },
};
