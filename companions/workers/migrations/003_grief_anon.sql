-- GriefRiver: anonymous sessions also need persona so the persona is preserved
-- through soft-wall signup into the messages table.

ALTER TABLE anonymous_sessions ADD COLUMN bot_persona TEXT DEFAULT 'river';
