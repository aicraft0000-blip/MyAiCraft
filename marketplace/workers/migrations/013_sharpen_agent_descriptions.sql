-- Sharpen catalog card descriptions for The Accountant, Scout, Counsel, Brief, Flight Test
-- to match the voice and specificity of Chief of Staff and The Director.

UPDATE products SET description = 'Most financial decisions that go wrong weren''t made on bad numbers. They were made on numbers nobody wanted to look at. The Accountant holds the picture you''ve been avoiding — cash, burn, margin, runway — and triggers a Red Flag the moment optimism starts driving the numbers instead of the numbers driving the decision.'
WHERE id = 'agent_accountant';

UPDATE products SET description = 'Every founder has a version of their customer that doesn''t quite exist. The Scout finds the real one — not by asking what they think, but by studying what they do. Reads conversations, reviews, churn signals, and support patterns. Tells you what your market has been trying to say while you weren''t listening.'
WHERE id = 'agent_scout';

UPDATE products SET description = 'Most founders find out what a contract actually said when it''s too late to negotiate. The Counsel reads what you''re about to sign — in plain English, with a risk register attached — and tells you what to push back on, what to accept, and when the moment calls for a real solicitor. Actual analysis, not disclaimers dressed up as advice.'
WHERE id = 'agent_counsel';

UPDATE products SET description = 'Employment disputes don''t wait for you to get prepared. The Brief operates the way a litigator does — it calculates your Tribunal deadlines before anything else, assesses your position without flattery, and names what the other side will argue before they do. Then it tells you exactly what to do next.'
WHERE id = 'agent_brief';

UPDATE products SET description = 'Most bugs get found by customers. Flight Test finds them first. Install it inside your project and it runs the tests your users would — purchase flows, download gates, error paths, edge cases — before they do. Every issue logged as a reproducible step sequence with severity rating and fix priority. Keeps a failure log so each sweep is sharper than the last.'
WHERE id = 'agent_qa';
