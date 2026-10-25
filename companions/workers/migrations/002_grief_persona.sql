-- GriefRiver: separate conversation threads per persona ('river' or 'grief')
-- Default 'river' so existing rows are categorised correctly.

ALTER TABLE messages ADD COLUMN bot_persona TEXT DEFAULT 'river';

CREATE INDEX IF NOT EXISTS idx_messages_account_persona_created
  ON messages (account_id, bot_persona, created_at);
