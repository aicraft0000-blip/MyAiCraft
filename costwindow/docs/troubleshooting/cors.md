# Troubleshooting — CORS Errors

## Symptom: Login fails silently — no error message, just nothing happens
**What it means:** Your frontend domain is not in the backend's allowed origins list. The browser blocks the request before it reaches the server.
**Fix:**
1. Open `backend/main.py`
2. Find the `allow_origins` line — it looks like:
```python
allow_origins=[settings.frontend_url, "http://localhost:5173", "https://costwindow.pages.dev"],
```
3. Add your new domain:
```python
allow_origins=[settings.frontend_url, "http://localhost:5173",
               "https://costwindow.pages.dev", "https://costwindow.com",
               "https://www.costwindow.com"],
```
4. Commit and push — Railway redeploys automatically

**This happens every time you add a new domain.** Adding a custom domain, moving from .pages.dev to your own domain, adding www — each one needs adding to this list.
