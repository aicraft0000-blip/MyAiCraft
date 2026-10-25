-- Marketplace catalog seed data
-- Run once after migration. Safe to re-run (INSERT OR IGNORE).

-- SKILLS
INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key) VALUES
('skill_post_writer',    'skill', 'Post Writer',            'post-writer',            'Social Content', 'Writes complete social posts — hook, body, and CTA — tailored to your brand voice and target platform. Install once, brief it once, get on-brand posts every time.',                                              'Claude, ChatGPT, Gemini, Perplexity', 700,  'skills/post-writer.md'),
('skill_post_grader',    'skill', 'Post Grader',            'post-grader',            'Social Content', 'Scores your post for virality across seven dimensions — hook strength, emotional charge, share-worthiness and more — then gives you the top three fixes ranked by impact.',                                    'Claude, ChatGPT, Gemini, Perplexity', 700,  'skills/post-grader.md'),
('skill_post_scheduler', 'skill', 'Post Scheduler',         'post-scheduler',         'Social Content', 'Schedules finished posts to your chosen platforms via Blotato. Handles single and multi-platform scheduling with pre-publish checks so nothing goes out wrong.',                                               'Claude Code required',                700,  'skills/post-scheduler.md'),
('skill_content_coach',  'skill', 'Content Coach',          'content-coach',          'Social Content', 'Your end-to-end social content guide — from blank page to scheduled post. Chains brand brief, ideation, writing, grading, and scheduling into one smooth workflow.',                                         'Claude, ChatGPT, Gemini, Perplexity', 900,  'skills/content-coach.md'),
('skill_url_video',      'skill', 'URL to Video Series',    'url-to-video-series',    'Video',          'Turns any URL into a stacked series of 3–5 short-form video briefs (30–60 seconds each), each with a hook, script, scene outline, caption, hashtags, and CTA back to the URL.',                             'Claude, ChatGPT, Gemini, Perplexity', 900,  'skills/url-to-video-series.md'),
('skill_vidbrief',       'skill', 'Vidbrief',               'vidbrief',               'Video',          'General-purpose engine for short-form social video briefs. Accepts a URL or topic, loads your brand voice, and outputs a full production brief for TikTok, Reels, Shorts, or LinkedIn video.',               'Claude, ChatGPT, Gemini, Perplexity', 700,  'skills/vidbrief.md'),
('skill_brand_brief',    'skill', 'Brand Brief',            'brand-brief',            'Brand',          'Captures your brand once — what you sell, who buys, the action you want readers to take, your voice — then saves it so every other content skill can use it automatically.',                                  'Claude, ChatGPT, Gemini, Perplexity', 500,  'skills/brand-brief.md'),
('skill_deploy',         'skill', 'Deploy',                 'deploy',                 'Developer',      'Executes your documented deployment process safely. Reads your DEPLOY.md recipe, presents the plan for approval, runs it step by step, and verifies success before finishing.',                               'Claude Code required',                700,  'skills/deploy.md'),
('skill_excalidraw',     'skill', 'Excalidraw Diagram',     'excalidraw-diagram',     'Productivity',   'Creates editable diagrams in Excalidraw from a description. Default for all diagram requests — from architecture maps to flowcharts and wireframes.',                                                         'Claude Code required',                700,  'skills/excalidraw-diagram.md'),
('skill_skill_builder',  'skill', 'Skill Builder Reference','skill-builder-reference','Developer',      'The technical reference for building your own Claude Code skills — frontmatter, patterns, argument passing, troubleshooting. Everything you need to create reusable AI instructions from scratch.',            'Claude Code required',                900,  'skills/skill-builder-reference.md'),
('skill_security',       'skill', 'Security Guardian',      'security-guardian',      'Security',       'Your personal AI security protocol. Triggers whenever a new risk appears — new tool connections, API keys, financial actions, unverified code, credential handling — and walks you through safe next steps.',  'Claude Code required',                1500, 'skills/security-guardian.md'),
('skill_security_failsafe','skill','Security Failsafe',     'security-failsafe',      'Security',       'An always-on protection protocol for AI assistants. Install once and your AI is permanently instructed to protect your API keys, finances, and identity — refusing to log credentials, flagging financial actions before taking them, and stopping to ask before connecting anything new. Works silently in the background so you can move fast without leaving yourself exposed.', 'Claude, ChatGPT, Gemini, Perplexity', 1900, 'skills/security-failsafe.md');

-- AGENTS
INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key) VALUES
('agent_finance',    'agent', 'Finance Command',   'finance-command',   'Business Ops', 'Your AI CFO for small business. Handles forecasting, budgeting, cash tracking, pricing signals, and financial risk alerts. Works from your own numbers and gives you plain-English insight, not jargon.',                            'Claude, ChatGPT, Gemini',             1500, 'agents/finance-command.md'),
('agent_marketing',  'agent', 'Customer Beacon',   'customer-beacon',   'Business Ops', 'Your go-to-market and community operations agent. Plans and runs campaigns, manages funnel analytics, operates your support desk, and feeds customer insights back into your product decisions.',                                     'Claude, ChatGPT, Gemini',             1500, 'agents/customer-beacon.md'),
('agent_legal',      'agent', 'Legal Ops',         'legal-ops',         'Business Ops', 'Handles contracts, compliance, privacy and AI policy, IP protection, and deal-desk reviews. Produces templates, flags risks, and keeps you on the right side of GDPR and consumer protection law.',                                  'Claude, ChatGPT, Gemini',             1500, 'agents/legal-ops.md'),
('agent_manuals',    'agent', 'Manual Factory',    'manual-factory',    'Productivity', 'Generates and maintains downloadable business manuals and documentation. Give it a topic, an outline, or an existing draft — it produces polished, structured documents you can share with your team or customers.',                  'Claude, ChatGPT, Gemini',             1200, 'agents/manual-factory.md'),
('agent_security',   'agent', 'Security Sentinel', 'security-sentinel', 'Security',     'On-demand safety sweeps across your repositories, documentation, and deployment surfaces. Identifies vulnerabilities, updates hooks, and keeps your security posture current without requiring a dedicated security team.',            'Claude Code required',                1500, 'agents/security-sentinel.md'),
('agent_qa',         'agent', 'Flight Test',       'flight-test',       'Developer',    'End-to-end QA agent. Runs scripted and exploratory tests, verifies your purchase and download flows work exactly as customers would experience them, and reports UX issues with reproducible steps and severity ratings.',             'Claude Code required',                1200, 'agents/flight-test.md');

-- BUNDLES
INSERT OR IGNORE INTO bundles (id, name, slug, description, price_pence) VALUES
('bundle_social',   'Social Content Pack', 'social-content-pack', 'Everything you need to write, score, and schedule social content — Post Writer, Post Grader, and Post Scheduler working together as one workflow.', 1500),
('bundle_video',    'Video Creator Pack',  'video-creator-pack',  'The full short-form video pipeline — Vidbrief, URL to Video Series, and Brand Brief. From any topic or link to a complete production brief in minutes.', 1600),
('bundle_biz_ops',  'Business Ops Pack',   'business-ops-pack',   'The back-office trio for small business — Finance Command, Legal Ops, and Manual Factory. CFO insight, legal protection, and professional documentation, all AI-powered.', 3200),
('bundle_security', 'Security Pack',       'security-pack',       'Complete AI security — the always-on Failsafe protocol, the Guardian for real-time risk checks, and the Sentinel agent for deep infrastructure sweeps. Three layers of protection, one price.', 3700);

-- BUNDLE ITEMS
INSERT OR IGNORE INTO bundle_items (bundle_id, product_id) VALUES
('bundle_social',   'skill_post_writer'),
('bundle_social',   'skill_post_grader'),
('bundle_social',   'skill_post_scheduler'),
('bundle_video',    'skill_vidbrief'),
('bundle_video',    'skill_url_video'),
('bundle_video',    'skill_brand_brief'),
('bundle_biz_ops',  'agent_finance'),
('bundle_biz_ops',  'agent_legal'),
('bundle_biz_ops',  'agent_manuals'),
('bundle_security', 'skill_security'),
('bundle_security', 'skill_security_failsafe'),
('bundle_security', 'agent_security');

-- FLAGSHIP AGENTS
INSERT OR IGNORE INTO products (id, type, name, slug, category, description, compatibility, price_pence, r2_key) VALUES
(
  "agent_director",
  "agent",
  "The Director",
  "the-director",
  "Creative",
  "Most people write prompts. The Director writes them the way a working creative director gives notes — specific, technical, opinionated, free of fluff. Tell it what you want to generate and which platform you are on. It returns a production-grade prompt in that model native language: Midjourney parameters, DALL-E prose, Stable Diffusion tags, Sora cinematic notes. Your specifics survive verbatim. The gaps are filled with informed craft defaults, named openly so you can correct in one line. Covers 12 image and video platforms. Gets sharper the more you use it.",
  "Claude, ChatGPT, Gemini, Claude Code",
  2900,
  "agents/the-director.md"
),
(
  "agent_chief_of_staff",
  "agent",
  "The Chief of Staff",
  "chief-of-staff",
  "Business Ops",
  "A real chief of staff does not schedule your calendar. They protect your thinking. Install this once and your AI becomes a senior operator embedded inside your working life — one that holds the whole picture, surfaces what you missed, pushes back when you need it, and tells you the truth even when it is inconvenient. On first contact it interviews you across seven sections, one question at a time. After that it maintains a living dossier that grows under your sign-off. It flags contradictions, surfaces silent risks, and names decisions you have been quietly postponing. No sycophancy. No performed warmth. Built for founders, operators, and people who run things.",
  "Claude, ChatGPT, Gemini, Claude Code",
  3500,
  "agents/chief-of-staff.md"
);
