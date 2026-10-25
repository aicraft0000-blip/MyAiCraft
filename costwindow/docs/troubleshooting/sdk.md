# Troubleshooting — CostWindow SDK

## Error: `ModuleNotFoundError: No module named 'costwindow'`
**What it means:** The SDK is installed in a different Python environment than the one your script is using.
**Fix:** Install the SDK in the correct virtual environment:
```bash
# If your project uses uv:
uv pip install -e /path/to/CostWindow-site/sdk --python /path/to/your/venv/bin/python

# If standard pip is available:
/path/to/your/venv/bin/python -m pip install -e /path/to/CostWindow-site/sdk
```
To find which Python your script uses: check its `run.sh` file for the `exec /path/...python` line.

## Error: `CostWindowProcessDisabledError` appearing unexpectedly
**What it means:** The kill switch was toggled OFF for that process in the dashboard.
**Fix:** Go to CostWindow → Dashboard → find the process row → click the toggle to re-enable it.

## Error: Costs not appearing in dashboard after running a script
**What it means:** Either the SDK can't reach the CostWindow backend, or the API key is wrong.
**Fix:**
1. Check that `COSTWINDOW_API_KEY` is being exported in your `run.sh`
2. Verify the key starts with `cw_live_`
3. Test the backend is reachable: `curl https://your-backend.up.railway.app/health`
4. Check `~/.costwindow/logs/costwindow.log` for silent error logs

## Costs appear as $0.00
**What it means:** The model name isn't in CostWindow's pricing table.
**Fix:** Open `backend/app/pricing.py`, add the model, redeploy Railway.
