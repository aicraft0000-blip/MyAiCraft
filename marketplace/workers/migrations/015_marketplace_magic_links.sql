-- Magic-link sign-in tokens for the marketplace library.
-- Replaces email-as-credential on /marketplace/api/library and downloads.
CREATE TABLE IF NOT EXISTS marketplace_magic_tokens (
  id          TEXT PRIMARY KEY,
  account_id  TEXT NOT NULL,
  token       TEXT NOT NULL UNIQUE,
  expires_at  TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mmt_token ON marketplace_magic_tokens(token);
CREATE INDEX IF NOT EXISTS idx_mmt_account ON marketplace_magic_tokens(account_id);
