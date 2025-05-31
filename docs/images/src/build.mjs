// Renders the README images in docs/images/ from the HTML pages next to this file.
//
// playwright-core and a Chromium build are needed. They are not repo
// dependencies; point the script at an existing install:
//
//   PLAYWRIGHT_CORE=/path/to/node_modules/playwright-core \
//   CHROMIUM=~/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
//   node docs/images/src/build.mjs [banner results results_search architecture]
//
// CHROMIUM is optional when playwright-core can find its own browser.
// The pages load the Gelasio and JetBrains Mono fonts from Google Fonts, so the
// build needs network access. Data comes from docs/results.json and
// docs/images/src/examples.json (written by examples.py, see its header).
import { createRequire } from 'node:module';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { homedir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, '..');
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

function findChromium() {
  if (process.env.CHROMIUM) return process.env.CHROMIUM;
  const base = join(homedir(), '.cache', 'ms-playwright');
  if (!existsSync(base)) return undefined;
  for (const d of readdirSync(base).sort().reverse()) {
    const exe = join(base, d, 'chrome-headless-shell-linux64', 'chrome-headless-shell');
    if (d.startsWith('chromium_headless_shell') && existsSync(exe)) return exe;
  }
  return undefined;
}

const data = {
  results: JSON.parse(readFileSync(resolve(here, '../../results.json'), 'utf8')),
  examples: JSON.parse(readFileSync(join(here, 'examples.json'), 'utf8')),
};

// name -> CSS width of the frame; everything renders at 2x.
const PAGES = { banner: 1280, results: 836, results_search: 836, architecture: 1500 };
const wanted = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(PAGES);

const browser = await chromium.launch({ executablePath: findChromium() });
for (const name of wanted) {
  const page = await browser.newPage({ viewport: { width: PAGES[name] + 40, height: 900 }, deviceScaleFactor: 2 });
  page.on('console', (m) => { if (m.type() === 'error') console.error(`${name}: ${m.text()}`); });
  page.on('pageerror', (e) => console.error(`${name}: ${e.message}`));
  await page.addInitScript((d) => { window.DATA = d; }, data);
  await page.goto(pathToFileURL(join(here, `${name}.html`)).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 15000 });
  const fonts = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family));
  if (!fonts.some((f) => f.includes('Gelasio'))) console.error(`${name}: Gelasio did not load, output uses a fallback serif`);
  const file = join(out, `${name}.png`);
  await page.locator('#frame').screenshot({ path: file });
  console.log(`wrote ${file}`);
  await page.close();
}
await browser.close();
