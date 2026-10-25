// radarwindow.com — serves the built SPA and proxies /api/* to the Railway
// backend (prefix stripped, matching the Vite dev proxy). Browser only ever
// talks to this origin, so the backend needs no CORS for production.

export default {
  // Keep-alive ping — stops Railway sleeping the backend between requests,
  // which froze the in-process job scheduler through its 07:00 slot.
  async scheduled(_event, env) {
    if (env.API_ORIGIN && !env.API_ORIGIN.includes("PLACEHOLDER")) {
      await fetch(`${env.API_ORIGIN}/health`).catch(() => {});
    }
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      if (!env.API_ORIGIN || env.API_ORIGIN.includes("PLACEHOLDER")) {
        return Response.json(
          { detail: "RadarWindow API is being provisioned — try again shortly." },
          { status: 503 },
        );
      }
      const upstream = new URL(env.API_ORIGIN);
      upstream.pathname = url.pathname.replace(/^\/api/, "") || "/";
      upstream.search = url.search;
      return fetch(new Request(upstream, request));
    }

    return env.ASSETS.fetch(request);
  },
};
