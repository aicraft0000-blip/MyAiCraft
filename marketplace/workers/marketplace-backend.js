const CORS_HEADERS = {
  'Access-Control-Allow-Origin': 'https://myaicraft.uk',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// D1-backed per-IP limiter for the LLM recommend endpoint (rate_limits table,
// per-minute windows, works across isolates). Fails open on DB error.
const RECOMMEND_LIMIT = 5;           // requests
const RECOMMEND_WINDOW_MS = 60_000;  // per minute
async function recommendRateLimited(env, ip) {
  const win = Math.floor(Date.now() / RECOMMEND_WINDOW_MS);
  try {
    const row = await env.DB.prepare(
      `INSERT INTO rate_limits (key, window, count) VALUES (?, ?, 1)
       ON CONFLICT(key, window) DO UPDATE SET count = count + 1
       RETURNING count`
    ).bind('rec:' + ip, win).first();
    if (row?.count === 1) {
      await env.DB.prepare('DELETE FROM rate_limits WHERE window < ?').bind(win - 2).run();
    }
    return (row?.count ?? 0) > RECOMMEND_LIMIT;
  } catch (e) {
    console.error('rate limit check failed:', e.message);
    return false;
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

function generateId() {
  return crypto.randomUUID().replace(/-/g, '').substring(0, 20);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });

    if (path === '/marketplace/api/products' && request.method === 'GET')
      return handleProducts(request, env);

    if (path === '/marketplace/api/recommend' && request.method === 'POST')
      return handleRecommend(request, env);

    if (path === '/marketplace/api/checkout' && request.method === 'POST')
      return handleCheckout(request, env);

    if (path === '/marketplace/api/webhook' && request.method === 'POST')
      return handleWebhook(request, env);

    if (path === '/marketplace/api/order' && request.method === 'GET')
      return handleOrder(request, env);

    if (path === '/marketplace/api/magic-link' && request.method === 'POST')
      return handleMagicLink(request, env);

    if (path === '/marketplace/api/library' && request.method === 'GET')
      return handleLibrary(request, env);

    if (path.startsWith('/marketplace/api/download/') && request.method === 'GET')
      return handleDownload(request, env);

    if (path.startsWith('/marketplace/api/free-download/') && request.method === 'GET')
      return handleFreeDownload(request, env);

    if (path.startsWith('/marketplace/api/file/free/') && (request.method === 'GET' || request.method === 'HEAD')) {
      const resp = await handleFileFree(request, env);
      return request.method === 'HEAD' ? new Response(null, { status: resp.status, headers: resp.headers }) : resp;
    }

    if (path.startsWith('/marketplace/api/file/') && (request.method === 'GET' || request.method === 'HEAD')) {
      const resp = await handleFile(request, env);
      return request.method === 'HEAD' ? new Response(null, { status: resp.status, headers: resp.headers }) : resp;
    }

    if (path === '/marketplace/health') return json({ ok: true });

    return json({ error: 'Not found' }, 404);
  },
};

// GET /marketplace/api/products
// Returns full catalog: skills, agents, bundles.
// Never returns r2_key or raw file content.
async function handleProducts(request, env) {
  try {
    const { results: products } = await env.DB.prepare(
      `SELECT id, type, name, slug, category, description, compatibility, price_pence, is_free, is_claude_skill
       FROM products WHERE active = 1 ORDER BY type, category, name`
    ).all();

    const { results: bundles } = await env.DB.prepare(
      `SELECT b.id, b.name, b.slug, b.description, b.price_pence,
              GROUP_CONCAT(p.name, '|') as product_names,
              GROUP_CONCAT(p.id, '|') as product_ids
       FROM bundles b
       JOIN bundle_items bi ON bi.bundle_id = b.id
       JOIN products p ON p.id = bi.product_id AND p.active = 1
       WHERE b.active = 1
       GROUP BY b.id ORDER BY b.name`
    ).all();

    const bundlesFormatted = bundles.map(b => ({
      ...b,
      product_names: b.product_names ? b.product_names.split('|') : [],
      product_ids: b.product_ids ? b.product_ids.split('|') : [],
    }));

    return new Response(JSON.stringify({ products, bundles: bundlesFormatted }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=300', ...CORS_HEADERS },
    });
  } catch (err) {
    console.error('handleProducts failed:', err.message);
    return json({ error: 'Failed to load catalog' }, 500);
  }
}

// POST /marketplace/api/recommend
// Body: { query: "I want to write social media posts" }
// CostWindow usage reporting — fire-and-forget, never blocks or breaks the request.
// Needs COSTWINDOW_API_KEY worker secret; silently skips if unset.
async function reportToCostWindow(env, label, model, inputTokens, outputTokens) {
  if (!env.COSTWINDOW_API_KEY) return;
  try {
    await fetch('https://your-backend.up.railway.app/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Api-Key': env.COSTWINDOW_API_KEY },
      body: JSON.stringify({
        label,
        provider: 'anthropic',
        model,
        input_tokens: inputTokens || 0,
        output_tokens: outputTokens || 0,
        cached_tokens: 0,
        billing_type: 'api',
      }),
      signal: AbortSignal.timeout(2000),
    });
  } catch (e) {
    console.error('CostWindow report failed:', e.message);
  }
}

// Calls Claude with the full catalog as context.
// Returns 2-4 recommended products/bundles with a "why" — no prices.
async function handleRecommend(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  if (await recommendRateLimited(env, ip)) return json({ error: 'Too many requests — please wait a minute.' }, 429);

  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const query = (body.query || '').trim();
  if (!query || query.length < 5) return json({ error: 'Query too short' }, 400);
  if (query.length > 500) return json({ error: 'Query too long' }, 400);

  // Build catalog context for Claude — names + descriptions only, no prices
  let products, bundles;
  try {
    ({ results: products } = await env.DB.prepare(
      `SELECT name, slug, type, category, description FROM products WHERE active = 1`
    ).all());
    ({ results: bundles } = await env.DB.prepare(
      `SELECT b.name, b.slug, b.description, GROUP_CONCAT(p.name, ', ') as includes
       FROM bundles b
       JOIN bundle_items bi ON bi.bundle_id = b.id
       JOIN products p ON p.id = bi.product_id
       WHERE b.active = 1 GROUP BY b.id`
    ).all());
  } catch (e) {
    console.error('handleRecommend DB error:', e.message);
    return json({ error: 'Failed to load catalog' }, 500);
  }

  const catalogText = [
    'SKILLS — quick to install, great starting point:',
    ...products.filter(p => p.type === 'skill').map(p => `  ${p.slug} | [SKILL] ${p.name} (${p.category}): ${p.description}`),
    '',
    'AGENTS — full AI specialists:',
    ...products.filter(p => p.type === 'agent').map(p => `  ${p.slug} | [AGENT] ${p.name} (${p.category}): ${p.description}`),
    '',
    'BUNDLES — discounted combinations:',
    ...bundles.map(b => `  ${b.slug} | [BUNDLE] ${b.name}: ${b.description} (Includes: ${b.includes})`),
  ].join('\n');

  const systemPrompt = `You are a helpful assistant for myaicraft.uk, a marketplace selling AI skills and agents.
A user has described what they are trying to accomplish. Recommend the most relevant items from the catalog.

Rules:
- Recommend 2 to 4 items maximum
- Always include at least one SKILL — they are quick to install and a great entry point
- Only include an AGENT if it is clearly a strong fit
- Prefer a BUNDLE when it covers the need well
- Do NOT mention prices
- The slug field in your response must exactly match the slug shown before the | in the catalog
- Output raw JSON only — no markdown fences, no explanation, just the JSON object

Catalog (format: slug | type name):
${catalogText}

Respond with exactly this JSON and nothing else:
{"recommendations":[{"slug":"SLUG_FROM_CATALOG","name":"NAME","type":"skill or agent or bundle","why":"One sentence."}]}`;

  let claudeResponse;
  try {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 600,
        system: systemPrompt,
        messages: [{ role: 'user', content: query }],
      }),
    });
    if (!resp.ok) return json({ error: 'Recommendation service unavailable' }, 503);
    const data = await resp.json();
    claudeResponse = data.content?.[0]?.text || '';
    await reportToCostWindow(env, 'marketplace-recommend', 'claude-sonnet-4-6',
      data.usage?.input_tokens, data.usage?.output_tokens);
  } catch (e) {
    return json({ error: 'Recommendation service unavailable' }, 503);
  }

  // Strip markdown fences if Claude added them, then extract the JSON object
  let jsonText = claudeResponse.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const jsonMatch = jsonText.match(/\{[\s\S]*\}/);
  if (jsonMatch) jsonText = jsonMatch[0];

  let parsed;
  try { parsed = JSON.parse(jsonText); } catch {
    return json({ error: 'Could not parse recommendations' }, 500);
  }

  return json({ recommendations: parsed.recommendations || [] });
}
// POST /marketplace/api/checkout
// Body: { items: [{type:'product'|'bundle', id:'...'}, ...], account_id: '...' }
// Creates a Stripe Checkout session and returns the URL.
async function handleCheckout(request, env) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const { items, account_id } = body;
  if (!items || !Array.isArray(items) || items.length === 0)
    return json({ error: 'No items in basket' }, 400);

  // Build line items
  const lineItems = [];
  try {
    for (const item of items) {
      if (item.type === 'product') {
        const product = await env.DB.prepare(
          'SELECT name, price_pence, is_free FROM products WHERE id = ? AND active = 1'
        ).bind(item.id).first();
        if (!product) return json({ error: `Product not found: ${item.id}` }, 404);
        if (product.is_free || product.price_pence <= 0)
          return json({ error: `${product.name} is free — use the free download, no checkout needed.` }, 400);
        lineItems.push({
          price_data: {
            currency: 'gbp',
            unit_amount: product.price_pence,
            product_data: { name: product.name },
          },
          quantity: 1,
        });
      } else if (item.type === 'bundle') {
        const bundle = await env.DB.prepare(
          'SELECT name, price_pence FROM bundles WHERE id = ? AND active = 1'
        ).bind(item.id).first();
        if (!bundle) return json({ error: `Bundle not found: ${item.id}` }, 404);
        lineItems.push({
          price_data: {
            currency: 'gbp',
            unit_amount: bundle.price_pence,
            product_data: { name: bundle.name },
          },
          quantity: 1,
        });
      } else {
        return json({ error: `Unknown item type: ${item.type}` }, 400);
      }
    }
  } catch (e) {
    console.error('handleCheckout DB error:', e.message);
    return json({ error: 'Failed to load item details' }, 500);
  }

  if (lineItems.length === 0) return json({ error: 'No valid items found' }, 400);

  // Build Stripe Checkout session via form-encoded body
  const stripeBody = new URLSearchParams({
    mode: 'payment',
    success_url: env.CHECKOUT_SUCCESS_URL + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url: env.CHECKOUT_CANCEL_URL,
    'metadata[account_id]': account_id || '',
    'metadata[items_json]': JSON.stringify(items),
  });
  lineItems.forEach((li, i) => {
    stripeBody.append(`line_items[${i}][price_data][currency]`, li.price_data.currency);
    stripeBody.append(`line_items[${i}][price_data][unit_amount]`, String(li.price_data.unit_amount));
    stripeBody.append(`line_items[${i}][price_data][product_data][name]`, li.price_data.product_data.name);
    stripeBody.append(`line_items[${i}][quantity]`, '1');
  });

  let session;
  try {
    const stripeResp = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: stripeBody.toString(),
    });
    if (!stripeResp.ok) return json({ error: 'Payment service unavailable' }, 503);
    session = await stripeResp.json();
  } catch (e) {
    return json({ error: 'Payment service unavailable' }, 503);
  }

  if (!session.url) return json({ error: 'Stripe error', detail: session.error?.message }, 500);

  return json({ url: session.url });
}

// POST /marketplace/api/webhook
// Stripe calls this after a successful payment.
// Verifies signature, then unlocks all purchased items in the customer's library.
async function handleWebhook(request, env) {
  const sig = request.headers.get('stripe-signature');
  const rawBody = await request.text();

  const isValid = await verifyStripeSignature(rawBody, sig, env.STRIPE_WEBHOOK_SECRET);
  if (!isValid) return new Response('Invalid signature', { status: 401, headers: CORS_HEADERS });

  let event;
  try { event = JSON.parse(rawBody); } catch { return new Response('Invalid JSON', { status: 400, headers: CORS_HEADERS }); }

  if (event.type !== 'checkout.session.completed')
    return new Response('Ignored', { status: 200, headers: CORS_HEADERS });

  const session = event.data.object;
  const email = session.customer_details?.email || '';
  const metaAccountId = (session.metadata?.account_id || '').trim();
  const account_id = metaAccountId || email;
  const itemsJson = session.metadata?.items_json || '[]';

  let items;
  try { items = JSON.parse(itemsJson); } catch { items = []; }

  try {
    const orderId = generateId();
    await env.DB.prepare(
      `INSERT INTO marketplace_orders (id, account_id, stripe_session_id, stripe_customer_email, status)
       VALUES (?, ?, ?, ?, 'completed')`
    ).bind(orderId, account_id, session.id, email).run();

    for (const item of items) {
      const orderItemId = generateId();
      if (item.type === 'product') {
        await env.DB.prepare(
          `INSERT INTO marketplace_order_items (id, order_id, product_id) VALUES (?, ?, ?)`
        ).bind(orderItemId, orderId, item.id).run();
        await env.DB.prepare(
          `INSERT OR IGNORE INTO marketplace_library (id, account_id, product_id, order_id)
           VALUES (?, ?, ?, ?)`
        ).bind(generateId(), account_id, item.id, orderId).run();
      } else if (item.type === 'bundle') {
        await env.DB.prepare(
          `INSERT INTO marketplace_order_items (id, order_id, bundle_id) VALUES (?, ?, ?)`
        ).bind(orderItemId, orderId, item.id).run();
        const { results: bundleProducts } = await env.DB.prepare(
          `SELECT product_id FROM bundle_items WHERE bundle_id = ?`
        ).bind(item.id).all();
        for (const bp of bundleProducts) {
          await env.DB.prepare(
            `INSERT OR IGNORE INTO marketplace_library (id, account_id, product_id, order_id)
             VALUES (?, ?, ?, ?)`
          ).bind(generateId(), account_id, bp.product_id, orderId).run();
        }
      }
    }
  } catch (e) {
    console.error('handleWebhook DB error:', e.message, 'session:', session.id);
    // Return 200 so Stripe does not retry — log the error for manual recovery
    return new Response('Error recorded', { status: 200, headers: CORS_HEADERS });
  }

  return new Response('OK', { status: 200, headers: CORS_HEADERS });
}

// Stripe signature verification using Web Crypto API (no Node.js crypto needed)
async function verifyStripeSignature(payload, sigHeader, secret) {
  try {
    if (!sigHeader) return false;
    const parts = sigHeader.split(',').reduce((acc, part) => {
      const [k, v] = part.split('=');
      acc[k] = v;
      return acc;
    }, {});
    const timestamp = parts['t'];
    const sig = parts['v1'];
    if (!timestamp || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false;
    const signedPayload = `${timestamp}.${payload}`;
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
    );
    const signatureBuffer = await crypto.subtle.sign('HMAC', key, encoder.encode(signedPayload));
    const computedSig = Array.from(new Uint8Array(signatureBuffer))
      .map(b => b.toString(16).padStart(2, '0')).join('');
    if (computedSig.length !== sig.length) return false;
    let diff = 0;
    for (let i = 0; i < computedSig.length; i++) {
      diff |= computedSig.charCodeAt(i) ^ sig.charCodeAt(i);
    }
    return diff === 0;
  } catch { return false; }
}
// GET /marketplace/api/order?session_id=xxx
// Returns order details (email, account_id, purchased items) for the post-checkout onboarding page.
async function handleOrder(request, env) {
  const url = new URL(request.url);
  const session_id = url.searchParams.get('session_id');
  if (!session_id) return json({ error: 'session_id required' }, 400);

  let order;
  try {
    order = await env.DB.prepare(
      `SELECT id, account_id, stripe_customer_email as email FROM marketplace_orders WHERE stripe_session_id = ?`
    ).bind(session_id).first();
  } catch (e) {
    console.error('handleOrder DB error:', e.message);
    return json({ error: 'Failed to look up order' }, 500);
  }

  if (!order) return json({ error: 'Order not found' }, 404);

  let items = [];
  try {
    const { results } = await env.DB.prepare(
      `SELECT ml.id as library_id, p.name, p.type, p.category, p.description, p.compatibility,
              CASE WHEN p.r2_key_compact IS NOT NULL THEN 1 ELSE 0 END as has_compact
       FROM marketplace_library ml
       JOIN products p ON p.id = ml.product_id
       WHERE ml.account_id = ?
       ORDER BY ml.created_at DESC`
    ).bind(order.account_id).all();
    items = results;
  } catch (e) {
    console.error('handleOrder library fetch error:', e.message);
  }

  // The Stripe session id is unguessable, so a valid one proves the purchase —
  // mint a library token here so the post-checkout page is signed in directly.
  let token = null;
  try {
    token = await mintLibraryToken(order.account_id, env);
  } catch (e) {
    console.error('handleOrder token mint error:', e.message);
  }

  return json({ email: order.email, account_id: order.account_id, items, token });
}

// ── Magic-link sign-in ─────────────────────────────────────────────
// Library access is authenticated by a bearer token, never by bare email.

const LIBRARY_TOKEN_DAYS = 30;

async function mintLibraryToken(accountId, env) {
  const token = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '');
  const expiresAt = new Date(Date.now() + LIBRARY_TOKEN_DAYS * 24 * 60 * 60 * 1000).toISOString();
  await env.DB.prepare(
    `INSERT INTO marketplace_magic_tokens (id, account_id, token, expires_at) VALUES (?, ?, ?, ?)`
  ).bind(generateId(), accountId, token, expiresAt).run();
  return token;
}

async function validateLibraryToken(token, env) {
  if (!token || token.length < 32) return null;
  const row = await env.DB.prepare(
    `SELECT account_id FROM marketplace_magic_tokens WHERE token = ? AND expires_at > datetime('now')`
  ).bind(token).first();
  return row ? row.account_id : null;
}

// POST /marketplace/api/magic-link  { email }
// Always responds with the same message so email addresses can't be probed.
async function handleMagicLink(request, env) {
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const email = (body.email || '').trim().toLowerCase();
  const genericOk = { ok: true, message: 'If that email has any purchases, a sign-in link is on its way.' };
  if (!email || !email.includes('@') || email.length > 200) return json(genericOk);

  try {
    const hasLibrary = await env.DB.prepare(
      `SELECT 1 FROM marketplace_library WHERE account_id = ? LIMIT 1`
    ).bind(email).first();
    if (!hasLibrary) return json(genericOk);

    // Rate limit: one link per address per 5 minutes
    const recent = await env.DB.prepare(
      `SELECT 1 FROM marketplace_magic_tokens WHERE account_id = ? AND created_at > datetime('now', '-5 minutes') LIMIT 1`
    ).bind(email).first();
    if (recent) return json(genericOk);

    const token = await mintLibraryToken(email, env);
    await sendLibraryLinkEmail(email, `https://myaicraft.uk/library.html?token=${token}`, env);
  } catch (e) {
    console.error('handleMagicLink error:', e.message);
  }
  return json(genericOk);
}

async function sendLibraryLinkEmail(email, url, env) {
  if (!env.MAILERSEND_API_KEY) {
    console.error('sendLibraryLinkEmail: MAILERSEND_API_KEY not set');
    return;
  }
  const html = '<h2>Your library sign-in link</h2><p>Click below to open your AiCraft library. The link stays valid for 30 days on this device.</p><p><a href="' + url + '" style="display:inline-block;background:#2A5C45;color:#fff;padding:12px 28px;border-radius:40px;text-decoration:none;font-weight:600;">Open my library</a></p><p style="color:#6b7280;font-size:0.85rem;">If you didn\'t request this, you can safely ignore this email.</p>';
  const res = await fetch('https://api.mailersend.com/v1/email', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + env.MAILERSEND_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: { email: env.MAILERSEND_FROM_EMAIL || 'noreply@myaicraft.uk', name: env.MAILERSEND_FROM_NAME || 'AiCraft' },
      to: [{ email }],
      subject: 'Your AiCraft library sign-in link',
      html,
      text: 'Open your AiCraft library: ' + url + '\n\nThe link stays valid for 30 days. If you didn\'t request this, ignore this email.',
    }),
  });
  if (!res.ok) console.error('sendLibraryLinkEmail failed:', res.status, await res.text());
}

// GET /marketplace/api/library?token=xxx
// Returns all products in the customer's library (no r2_key exposed).
async function handleLibrary(request, env) {
  const url = new URL(request.url);
  const account_id = await validateLibraryToken(url.searchParams.get('token'), env);
  if (!account_id) return json({ error: 'Sign-in link required or expired' }, 401);

  try {
    const { results } = await env.DB.prepare(
      `SELECT ml.id as library_id, p.id as product_id, p.name, p.type, p.category,
              p.description, p.compatibility, ml.created_at as purchased_at,
              CASE WHEN p.r2_key_compact IS NOT NULL THEN 1 ELSE 0 END as has_compact
       FROM marketplace_library ml
       JOIN products p ON p.id = ml.product_id
       WHERE ml.account_id = ?
       ORDER BY ml.created_at DESC`
    ).bind(account_id).all();

    return json({ library: results, email: account_id });
  } catch (e) {
    console.error('handleLibrary DB error:', e.message);
    return json({ error: 'Failed to load library' }, 500);
  }
}

// GET /marketplace/api/download/:library_id?token=xxx
// Returns a download URL served by this worker (R2 bindings cannot create signed URLs).
async function handleDownload(request, env) {
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  const libraryId = pathParts[pathParts.length - 1];
  const token = url.searchParams.get('token');
  const account_id = await validateLibraryToken(token, env);

  const edition = url.searchParams.get('edition') || 'full';
  if (!account_id) return json({ error: 'Sign-in link required or expired' }, 401);
  if (!libraryId) return json({ error: 'Missing parameters' }, 400);

  let item;
  try {
    item = await env.DB.prepare(
      `SELECT ml.id, p.r2_key, p.r2_key_compact, p.name
       FROM marketplace_library ml
       JOIN products p ON p.id = ml.product_id
       WHERE ml.id = ? AND ml.account_id = ?`
    ).bind(libraryId, account_id).first();
  } catch (e) {
    console.error('handleDownload DB error:', e.message);
    return json({ error: 'Failed to verify library access' }, 500);
  }

  if (!item) return json({ error: 'Item not found in library' }, 404);

  const fileUrl = `${url.origin}/marketplace/api/file/${encodeURIComponent(libraryId)}?token=${encodeURIComponent(token)}&edition=${encodeURIComponent(edition)}`;
  return json({ url: fileUrl, name: item.name, edition });
}

// GET /marketplace/api/file/:library_id?token=xxx&edition=full|compact
// Streams the purchased file from R2 after re-checking library access.
async function handleFile(request, env) {
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  const libraryId = pathParts[pathParts.length - 1];
  const account_id = await validateLibraryToken(url.searchParams.get('token'), env);
  const edition = url.searchParams.get('edition') || 'full';
  if (!account_id) return json({ error: 'Sign-in link required or expired' }, 401);
  if (!libraryId) return json({ error: 'Missing parameters' }, 400);

  let item;
  try {
    item = await env.DB.prepare(
      `SELECT ml.id, p.r2_key, p.r2_key_compact, p.name
       FROM marketplace_library ml
       JOIN products p ON p.id = ml.product_id
       WHERE ml.id = ? AND ml.account_id = ?`
    ).bind(libraryId, account_id).first();
  } catch (e) {
    console.error('handleFile DB error:', e.message);
    return json({ error: 'Failed to verify library access' }, 500);
  }

  if (!item) return json({ error: 'Item not found in library' }, 404);

  const r2Key = (edition === 'compact' && item.r2_key_compact) ? item.r2_key_compact : item.r2_key;
  return streamR2File(env, r2Key, item.name);
}

// GET /marketplace/api/file/free/:slug
// Streams a free product file from R2 — only for products with is_free = 1.
async function handleFileFree(request, env) {
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  const slug = pathParts[pathParts.length - 1];
  if (!slug) return json({ error: 'Missing slug' }, 400);

  let product;
  try {
    product = await env.DB.prepare(
      `SELECT name, r2_key, is_free FROM products WHERE slug = ? AND active = 1`
    ).bind(slug).first();
  } catch (e) {
    console.error('handleFileFree DB error:', e.message);
    return json({ error: 'Failed to look up product' }, 500);
  }

  if (!product) return json({ error: 'Product not found' }, 404);
  if (!product.is_free) return json({ error: 'This product is not free' }, 403);

  return streamR2File(env, product.r2_key, product.name);
}

// Stream an object from the R2 bucket as a file download.
async function streamR2File(env, r2Key, displayName) {
  let obj;
  try {
    obj = await env.MARKETPLACE_FILES.get(r2Key);
  } catch (e) {
    console.error('streamR2File R2 error:', e.message, 'key:', r2Key);
    return json({ error: 'Failed to fetch file' }, 500);
  }
  if (!obj) {
    console.error('streamR2File: object not found for key', r2Key);
    return json({ error: 'File not found' }, 404);
  }

  const extMatch = (r2Key || '').match(/\.[a-z0-9]+$/i);
  const safeName = (displayName || 'download').replace(/[^a-zA-Z0-9 ._-]/g, '') + (extMatch ? extMatch[0] : '');
  const headers = new Headers(CORS_HEADERS);
  headers.set('Content-Type', obj.httpMetadata?.contentType || 'application/octet-stream');
  headers.set('Content-Disposition', `attachment; filename="${safeName}"`);
  if (obj.size != null) headers.set('Content-Length', String(obj.size));
  return new Response(obj.body, { headers });
}

// GET /marketplace/api/free-download/:slug
// No authentication required — only works for products with is_free = 1.
async function handleFreeDownload(request, env) {
  const url = new URL(request.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  const slug = pathParts[pathParts.length - 1];

  if (!slug) return json({ error: 'Missing slug' }, 400);

  let product;
  try {
    product = await env.DB.prepare(
      `SELECT name, r2_key, is_free FROM products WHERE slug = ? AND active = 1`
    ).bind(slug).first();
  } catch (e) {
    console.error('handleFreeDownload DB error:', e.message);
    return json({ error: 'Failed to look up product' }, 500);
  }

  if (!product) return json({ error: 'Product not found' }, 404);
  if (!product.is_free) return json({ error: 'This product is not free' }, 403);

  const fileUrl = `${url.origin}/marketplace/api/file/free/${encodeURIComponent(slug)}`;
  return json({ url: fileUrl, name: product.name });
}
