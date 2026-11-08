# Current state (update when it changes)

Last checked: 8 November 2026 (after the second upload)

- **Domain and hosting:** myaicraft.uk. The files live on SiteGround (`public_html`, managed in SiteGround's File Manager) and Cloudflare sits in front. Confirmed from the live site's response headers on 8 November 2026.
- **Cloudflare bot protection** injects a script on every page and sets one cookie, `cf_clearance`. The pages say so.
- **Cloudflare Worker `myaicraft-edge`** runs in front of the whole site (made 7 July 2026). It redirects old addresses (`/privacy`, `/terms`, old grief paths), hides retired files, adds security headers, and handles missing pages. Its source is in `edge/myaicraft-edge.js`. Until 8 November 2026 it also served its own hard-coded `robots.txt`, `sitemap.xml` and an old 404 page, which is why uploading those files changed nothing. The version in `edge/` serves the uploaded files and `404.html` instead. Kay deploys it by pasting it into the Cloudflare dashboard.
- **Publishing:** by hand for now. Someone uploads the files from `site/` to SiteGround (Kay, or a Claude session on her computer). Until Cloudflare Pages is connected, a merged green-lane change is only live after the next upload, so say so in the summary to Kay.
- **Pages that stay Kay's and live outside `site/`:** the whitepaper, Quesi (`AICQindex.html`, `Qaccount.html`), River (`AICRindex.html`, `Raccount.html`, `Rchat.html`), River for grief (`grief/`), the privacy policy and terms. They're on the live site already; the versions in `website/` here have placeholders and must not be uploaded over the live ones.
- **Retired, unlinked, still on the server:** the shop (`catalog.html`, `library.html`), the old homepage sections, `about.html`, TradesDesk (`tradesdesk/`, still has forms that collect names and emails).
- **Weekly session:** Mondays at 10:40 UK time, in the myAIcraft cloud environment (which can reach radarwindow.com and myaicraft.uk).
- **RadarWindow public briefs:** the newest public one is from 29 August 2026. Either publishing stopped or new briefs aren't being made public. Kay to check.
- **Moltbook:** agent `myaicraft`, claimed and active since 8 November 2026, through the myAIcraft X account and a separate Gmail address used only for Moltbook. The API key is stored as a network secret on the myAIcraft cloud environment and is sent only to www.moltbook.com. It is not in any file. Nothing posted yet.
- **Moltbook owner details are public:** any agent can see the claiming X account's handle, name, picture and bio through the API. Kay's personal X account should not be used to claim.
