-- Mark content-coach, brand-brief, post-writer, post-grader, post-scheduler as free Claude Skills.
ALTER TABLE products ADD COLUMN is_claude_skill INTEGER NOT NULL DEFAULT 0;
UPDATE products SET is_free = 1, is_claude_skill = 1
  WHERE id IN ('skill_content_coach', 'skill_brand_brief', 'skill_post_writer', 'skill_post_grader', 'skill_post_scheduler');
