# Troubleshooting — Supabase

## Error: `pkce_cookie_missing` on registration or login
**What it means:** Supabase is sending the auth redirect to a URL that doesn't match your Site URL setting. The cookie can't be set across domains.
**Fix:**
1. Go to Supabase dashboard → Authentication → URL Configuration
2. Set Site URL to your live domain (e.g. `https://costwindow.com`)
3. Under Redirect URLs, add:
   - `https://costwindow.com`
   - `https://costwindow.com/**`
   - `https://costwindow.pages.dev` (if still using this)
4. Click Save and try again

## Error: Password reset email opens `localhost:3000`
**What it means:** Supabase Site URL is still pointing to your local development address.
**Fix:** Same as above — update Site URL to your live domain.

## Remember: update Site URL when your domain changes
If you add a custom domain after first going live (e.g. moved from `costwindow.pages.dev` to `costwindow.com`), you must update Site URL in Supabase again. The auth emails use whatever Site URL was set at the time of the request.
