-- Cache WRITES cost 25% more than regular input and were previously unpriced.
-- For conversation agents (Hermes/Scor, Claude Code) this is most of the bill —
-- Scor's June spend was undercounted ~60% without it.

ALTER TABLE public.api_calls ADD COLUMN IF NOT EXISTS cache_write_tokens INTEGER NOT NULL DEFAULT 0;
