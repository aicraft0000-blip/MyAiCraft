# Troubleshooting — AI CLI Tools

## Claude Code
- Full support — recommended for first-time setup
- Session hook installed at `~/.claude/settings.json` (the Stop hook)
- Session logs at `~/.claude/usage-data/session-meta/`
- If the hook isn't firing: type `/hooks` in Claude Code to reload config

## OpenAI Codex
- Full support — paste the setup prompt and approve each bash step when asked
- If Codex asks "should I run this command?" — answer yes for each setup step
- Session log location differs from Claude Code — the hook script reads from the Codex path

## OpenClaw
- Paste the setup prompt into an OpenClaw workspace session
- Enable file read/write and bash execution in OpenClaw settings before starting

## Hermes
- Run the setup prompt via `hermes run "..."` or paste into an active Hermes session
- If it stalls on a wizard question, answer manually in the terminal: `python3 tools/scanner/scanner.py --api-key cw_live_...`

## Termux (Android)
- Install Python and git first: `pkg install python git`
- The session log hook is not supported on Termux (no persistent log files)
- Use manual entry in the CostWindow dashboard for session costs
