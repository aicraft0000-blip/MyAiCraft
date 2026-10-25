# Troubleshooting — Frontend Hosting

## Dashboard

### Error: "Failed to load data" on the dashboard
**What it means:** Your login session has expired. The dashboard can't fetch data because your token is no longer valid.
**Fix:** Click **Sign out** in the top-right corner, then sign back in. The dashboard will load normally.

> If you see a **↻ Retry** button alongside the error, clicking it will attempt to reload — but if the session has expired, you'll need to sign out and back in regardless.

---

## Cloudflare Pages

### Error: No "Vite" framework preset available
**What it means:** Cloudflare Pages doesn't have a standalone Vite preset.
**Fix:** Select **None** as the framework and set manually:
- Build command: `npm run build`
- Output directory: `dist`
- Root directory: `frontend`

### Error: Custom domain shows "Verifying" for a long time
**What it means:** DNS is propagating. Usually resolves in minutes if your domain is already managed by Cloudflare, up to 48 hours otherwise.
**Fix:** Wait. You can use the `costwindow.pages.dev` URL in the meantime.

---

## Vercel

### Error: Build succeeds but dashboard shows a blank page
**What it means:** `VITE_API_URL` environment variable is not set, so API calls fail silently.
**Fix:**
1. Go to Vercel project → Settings → Environment Variables
2. Add `VITE_API_URL` = `https://your-backend.up.railway.app`
3. Redeploy (environment variables only apply to new deployments)

---

## Netlify

### Error: Page returns 404 on refresh
**What it means:** Netlify doesn't know to serve `index.html` for all routes — it looks for actual files.
**Fix:** Create `frontend/public/_redirects` containing exactly:
```
/* /index.html 200
```
Commit and redeploy.
