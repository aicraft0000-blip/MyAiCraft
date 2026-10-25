# Troubleshooting — Backend Hosting

## Railway

### Error: "Generate Domain" button is greyed out
**What it means:** Railway needs to know which port your app listens on before it can assign a domain.
**Fix:**
1. Go to Settings → Networking
2. Enter `8080` in the port field
3. Click Generate Domain — it activates immediately

### Error: GitHub repo not found when connecting
**What it means:** Railway's GitHub App hasn't been given permission to see your private repo.
**Fix:**
1. In Railway, click "Configure GitHub App"
2. You'll be taken to GitHub — under Repository access, select "Only select repositories"
3. Add your `costwindow-site` repo
4. Click Save, return to Railway, try again

### Error: Deployment successful but app crashes immediately
**What it means:** A Python package is missing from `requirements.txt`. Railway installs fresh — it only has what's listed.
**Fix:**
1. Click Logs in Railway
2. Look for `ModuleNotFoundError: No module named 'X'`
3. Add `X` to `backend/requirements.txt`
4. Push to GitHub — Railway redeploys automatically

### How to read Railway logs
Click Logs in the left panel. Errors appear in red. Scroll to the bottom for the most recent. If the app crashed, look for `Traceback` — the line at the bottom of the traceback is the actual error.

---

## Render

### Error: First request after idle is very slow
**What it means:** Render's free tier spins down after 15 minutes of inactivity. The first request wakes it up, which takes ~30 seconds.
**Fix:** Either upgrade to a paid tier, or accept the cold start. The dashboard will appear slow to load on first open after a period of no use.

### Error: Environment variables not taking effect
**What it means:** Render requires a redeploy after adding environment variables — they don't apply retroactively.
**Fix:** After adding variables under Environment tab → click Manual Deploy → Deploy latest commit.

---

## Fly.io

### Error: `fly deploy` fails with "app name already taken"
**What it means:** App names on Fly.io are globally unique across all users.
**Fix:** Open `backend/fly.toml`, change the `app` field to something unique (e.g. `costwindow-yourname`), then run `fly deploy` again.

### Error: Environment variables not set
**What it means:** Fly.io uses secrets, not a .env file.
**Fix:** Run for each variable:
```bash
fly secrets set SUPABASE_URL=your-value
fly secrets set SUPABASE_ANON_KEY=your-value
```
