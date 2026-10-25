#!/usr/bin/env node
/**
 * Mobile render gate.
 *
 * Fails the build if a visitor on a phone cannot reach the sign-in or
 * register controls, or if a page scrolls sideways.
 *
 * Why this exists: between 2026-07-05 and 2026-09-03 the landing nav pushed
 * "Sign in" and "Start free" outside the viewport on every phone width. The
 * page did NOT scroll horizontally -- `.lp` sets `overflow-x: hidden`, so the
 * buttons were clipped out of existence rather than pushed into a scrollable
 * area. Any check that only looked for horizontal scroll passed the whole time.
 * The load-bearing assertion here is therefore hit-testability, not scrollWidth.
 */
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname, resolve } from 'node:path';

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('✗ playwright is not installed.\n' +
    '  It is deliberately NOT a project dependency, so it never enters the\n' +
    '  Cloudflare Pages production build. To run this check locally:\n\n' +
    '    npm install --no-save playwright && npx playwright install chromium\n');
  process.exit(2);
}

const TARGET = process.argv[2] ?? 'dist';
const IS_URL = /^https?:\/\//i.test(TARGET);
const DIST = IS_URL ? null : resolve(TARGET);
const PORT = Number(process.env.RENDER_CHECK_PORT ?? 4399);
const ROUTES = ['/', '/how-it-works', '/login', '/register'];
const WIDTHS = [320, 360, 390, 430];
const AUTH_CTA = /sign in|log in|start free|register|get started|create account/i;

const MIME = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
  '.png':'image/png', '.svg':'image/svg+xml', '.json':'application/json',
  '.ico':'image/x-icon', '.woff2':'font/woff2', '.webmanifest':'application/manifest+json' };

if (!IS_URL && !existsSync(DIST)) {
  console.error(`✗ no build at ${DIST} — run \`npm run build\` first`);
  process.exit(2);
}

// Static server with SPA fallback so client-side routes resolve.
const server = createServer(async (req, res) => {
  const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
  let file = join(DIST, url === '/' ? 'index.html' : url);
  if (!existsSync(file) || !extname(file)) file = join(DIST, 'index.html');
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
});

function probe(ctaPattern) {
  const re = new RegExp(ctaPattern, 'i');
  const vw = window.innerWidth;
  const doc = document.documentElement, body = document.body;
  const scrollW = Math.max(doc.scrollWidth, body.scrollWidth);

  const header = document.querySelector('header, nav, .lp-nav') || document.body;
  const ctas = [];
  for (const el of header.querySelectorAll('a, button')) {
    const text = (el.textContent || '').trim();
    if (!re.test(text)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;

    const cx = Math.round(r.left + r.width / 2);
    const cy = Math.round(r.top + r.height / 2);
    const inViewport = r.left >= -1 && r.right <= vw + 1 && cy >= 0 && cy <= window.innerHeight;
    const hit = inViewport ? document.elementFromPoint(cx, cy) : null;
    const hittable = !!(hit && (hit === el || el.contains(hit) || hit.contains(el)));

    ctas.push({ text: text.slice(0, 30), left: Math.round(r.left), right: Math.round(r.right),
                inViewport, hittable });
  }
  return { vw, scrollW, hScroll: scrollW > vw + 1, ctas };
}

const failures = [];
const BASE = IS_URL ? TARGET.replace(/\/$/, '') : `http://127.0.0.1:${PORT}`;
if (!IS_URL) await new Promise((r) => server.listen(PORT, '127.0.0.1', r));
console.log(`Checking ${IS_URL ? 'LIVE SITE' : 'local build'}: ${BASE}`);

const browser = await chromium.launch({
  args: ['--no-sandbox'],
  ...(process.env.RENDER_CHECK_CHROMIUM ? { executablePath: process.env.RENDER_CHECK_CHROMIUM } : {}),
});
const ctx = await browser.newContext();
// Block anything off-box so third-party fonts/analytics can't hang or skew the run.
if (!IS_URL) {
  // Local mode: block off-box requests so third-party fonts can't hang the run.
  await ctx.route('**/*', (route) =>
    route.request().url().includes('127.0.0.1') ? route.continue() : route.abort());
}

for (const route of ROUTES) {
  for (const width of WIDTHS) {
    const page = await ctx.newPage();
    await page.setViewportSize({ width, height: 844 });
    const jsErrors = [];
    page.on('pageerror', (e) => jsErrors.push(String(e).slice(0, 140)));

    try {
      await page.goto(`${BASE}${route}`, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(350);
      const r = await page.evaluate(probe, AUTH_CTA.source);

      for (const c of r.ctas) {
        if (!c.inViewport)
          failures.push(`${route} @${width}px — "${c.text}" is outside the viewport (x ${c.left}..${c.right}, viewport 0..${width}). Unreachable: the page does not scroll sideways, so it is clipped away entirely.`);
        else if (!c.hittable)
          failures.push(`${route} @${width}px — "${c.text}" is in the viewport but not clickable (something is covering it).`);
      }
      if (r.hScroll)
        failures.push(`${route} @${width}px — page scrolls horizontally (${r.scrollW}px of content in a ${width}px viewport).`);
      for (const e of jsErrors)
        failures.push(`${route} @${width}px — JS error: ${e}`);
    } catch (err) {
      failures.push(`${route} @${width}px — failed to load: ${String(err).slice(0, 140)}`);
    }
    await page.close();
  }
}

await browser.close();
if (!IS_URL) server.close();

const checks = ROUTES.length * WIDTHS.length;
if (failures.length) {
  console.error(`\n✗ Mobile render gate FAILED — ${failures.length} problem(s) across ${checks} page/width combinations:\n`);
  for (const f of failures) console.error(`  • ${f}`);
  console.error(IS_URL
    ? `\nThe LIVE SITE is broken for phone visitors right now.\n`
    : `\nA phone visitor cannot sign in or register. Do not ship this.\n`);
  process.exit(1);
}
console.log(`✓ Mobile render gate passed — ${checks} page/width combinations, all auth CTAs reachable.`);
