-- Web chat support: unified message history across channels + anonymous sessions
-- Safe to apply to live DB: new tables + additive ALTERs only, all existing reads/writes unaffected.

-- 1. Single source of truth for conversation history across all channels.
CREATE TABLE IF NOT EXISTS messages (
  id              TEXT PRIMARY KEY,
  account_id      TEXT NOT NULL,
  linked_user_id  TEXT,
  channel         TEXT NOT NULL,
  role            TEXT NOT NULL,
  content         TEXT NOT NULL,
  tokens          INTEGER,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_account_created
  ON messages (account_id, created_at);

-- 2. Extend linked_users to support web sessions (telegram_user_id becomes optional).
ALTER TABLE linked_users ADD COLUMN channel TEXT DEFAULT 'telegram';
ALTER TABLE linked_users ADD COLUMN web_session_token TEXT;

CREATE INDEX IF NOT EXISTS idx_linked_users_web_session_token
  ON linked_users (web_session_token);

-- 3. Anonymous web sessions for the soft-wall flow (5 free messages before signup).
CREATE TABLE IF NOT EXISTS anonymous_sessions (
  token           TEXT PRIMARY KEY,
  message_count   INTEGER DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  promoted_to     TEXT
);

-- 4. Anonymous messages live in their own table until the visitor signs up.
--    On signup, rows are migrated into the messages table under the new account_id.
CREATE TABLE IF NOT EXISTS anonymous_messages (
  id              TEXT PRIMARY KEY,
  session_token   TEXT NOT NULL,
  role            TEXT NOT NULL,
  content         TEXT NOT NULL,
  tokens          INTEGER,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_anonymous_messages_token_created
  ON anonymous_messages (session_token, created_at);
