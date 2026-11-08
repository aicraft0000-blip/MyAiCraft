// myaicraft-edge: the Cloudflare Worker in front of myaicraft.uk.
// It upgrades http to https, redirects a few old addresses, hides retired
// files and adds security headers. Pages in the repo's site/ folder are
// served from Cloudflare Pages, which publishes them straight from GitHub.
// Everything else (Kay's own pages, the companions, images) still comes
// from SiteGround. Missing pages get site/404.html.

// Set PAGES_ORIGIN as a variable on the Worker if the Pages address differs.
const DEFAULT_PAGES_ORIGIN = "https://myaicraft-site.pages.dev";

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

function withHeaders(resp, status) {
  const out = new Response(resp.body, { status: status || resp.status, headers: resp.headers });
  out.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  out.headers.set("X-Content-Type-Options", "nosniff");
  out.headers.set("X-Frame-Options", "SAMEORIGIN");
  out.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  return out;
}

async function notFound(pages) {
  try {
    const page = await fetch(pages + "/404.html");
    if (page.ok || page.status === 404) {
      const r = withHeaders(page, 404);
      r.headers.set("Content-Type", "text/html; charset=utf-8");
      return r;
    }
  } catch (e) {}
  return new Response(FALLBACK_404, { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

export default {
  async fetch(request, env) {
    const pages = (env && env.PAGES_ORIGIN) || DEFAULT_PAGES_ORIGIN;
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
      if (GONE.has(path)) {
        return notFound(pages);
      }

      // 1. Pages first, for plain page requests.
      if (request.method === "GET" || request.method === "HEAD") {
        const fromPages = await fetch(pages + path + url.search, { method: request.method, redirect: "follow" });
        if (fromPages.status !== 404) {
          const resp = withHeaders(fromPages);
          // pages.dev can mark its own copies "noindex"; that must not leak onto myaicraft.uk.
          resp.headers.delete("X-Robots-Tag");
          return resp;
        }
      }

      // 2. Otherwise SiteGround, as before.
      if (url.hostname !== "myaicraft.uk" && url.hostname !== "www.myaicraft.uk") {
        url.hostname = "myaicraft.uk";
        request = new Request(url.toString(), request);
      }
      const origin = await fetch(request);
      if (origin.status === 404 && (request.headers.get("Accept") || "").includes("text/html")) {
        return notFound(pages);
      }
      return withHeaders(origin);
    } catch (e) {
      return fetch(request);
    }
  },
};
