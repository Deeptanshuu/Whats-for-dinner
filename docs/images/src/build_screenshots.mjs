// Regenerates docs/images/app-*.png from the real app talking to the real API.
//
// Start the two servers first (from the repo root unless noted):
//   PORT=5057 python -m server.app
//   cd web && VITE_API_URL=http://localhost:5057 npm run dev -- --port 5174
//
// Then run (playwright-core is not a repo dependency, so point NODE_PATH at an install):
//   NODE_PATH=/path/to/node_modules node docs/images/src/build_screenshots.mjs
// or set PLAYWRIGHT_CORE=/path/to/node_modules/playwright-core/index.mjs.
//
// Georgia is not installed on Linux, so the script injects Gelasio (metric
// compatible) under the name 'Georgia' for the capture only. The app is untouched.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const pw = process.env.PLAYWRIGHT_CORE ? await import(process.env.PLAYWRIGHT_CORE) : require('playwright-core');
const chromium = pw.chromium || pw.default.chromium;

const APP = process.env.APP_URL || 'http://localhost:5174';
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FONT_CSS = 'https://fonts.googleapis.com/css2?family=Gelasio:wght@400;600;700';
const INGREDIENTS = ['Paneer', 'Spinach Leaves', 'Turmeric powder', 'Green Chillies'];

// Gelasio css with the family renamed to Georgia.
const fontCss = (await (await fetch(FONT_CSS, { headers: { 'User-Agent': 'Mozilla/5.0 Chrome/120 Safari/537.36' } })).text())
  .replace(/font-family:\s*'Gelasio'/g, "font-family: 'Georgia'");

// Set CHROMIUM_PATH if playwright-core cannot find its own browser build.
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();

async function open(url) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.addStyleTag({ content: fontCss });
  await page.evaluate(() => document.fonts.ready);
}

// Wait for every img to load; reload the broken ones once.
async function imagesReady() {
  const pending = () =>
    page.evaluate(async () => {
      const imgs = [...document.querySelectorAll('img')];
      await Promise.all(
        imgs.map((i) => (i.complete ? null : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 15000); })))
      );
      return imgs.filter((i) => !i.complete || i.naturalWidth === 0).length;
    });
  await page.waitForLoadState('networkidle').catch(() => {});
  let bad = await pending();
  if (bad) {
    await page.evaluate(() => document.querySelectorAll('img').forEach((i) => {
      if (i.naturalWidth === 0) { const s = i.src; i.src = ''; i.src = s; }
    }));
    bad = await pending();
  }
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  const ph = await page.locator('.shadow-xl svg.lucide-utensils').count();
  console.log('imgs not loaded:', bad, '| cards showing the placeholder instead of a photo:', ph);
}

const titles = () => page.$$eval('.result .shadow-xl h2', (els) => els.map((e) => e.textContent).slice(0, 3));
const timing = () => page.locator('text=Execution Time').locator('..').locator('..').innerText();
const shot = (name, opts = {}) => page.screenshot({ path: path.join(OUT, name), ...opts });

// 1. ingredients mode
await open(APP);
await page.getByRole('button', { name: 'Veg Mode' }).or(page.getByLabel('Toggle vegetarian')).first().click().catch(() => {});
await page.locator('button[aria-pressed]').filter({ has: page.locator('.sr-only') }).first().click().catch(() => {});
for (const name of INGREDIENTS) {
  await page.getByPlaceholder('Search ingredients...').fill(name);
  await page.getByRole('button', { name, exact: true }).click();
}
await page.getByRole('button', { name: 'Find Recipes' }).click();
await page.waitForSelector('text=Execution Time');
await imagesReady();
await page.evaluate(() => window.scrollTo(0, 0));
console.log('ingredients', await titles(), await timing());
await shot('app-ingredients.png');

// 4. models: switch to TF-IDF on the same query
const firstResult = await page.$eval('.result .shadow-xl h2', (e) => e.textContent);
await page.getByRole('radio', { name: 'TF-IDF' }).click();
await page.waitForFunction(() => document.body.innerText.includes('Method: TF-IDF'));
await imagesReady();
await page.evaluate(() => window.scrollTo(0, 0));
console.log('tfidf', await titles(), await timing());
const pick = page.getByRole('radiogroup', { name: 'Recommendation model' });
const a = await pick.locator('xpath=..').boundingBox();
const b = await page.locator('text=Execution Time').locator('xpath=ancestor::div[contains(@class,"rounded-lg")][1]').boundingBox();
await shot('app-models.png', {
  clip: { x: 0, y: Math.max(0, a.y - 20), width: 1440, height: b.y + b.height + 20 - Math.max(0, a.y - 20) },
});

// 2. describe mode
await page.getByRole('tab', { name: 'Describe it' }).click();
await page.getByLabel('Describe what you feel like eating').fill('something creamy and spicy with spinach');
await page.getByRole('button', { name: 'Find Recipes' }).click();
await page.waitForSelector('text=Method: Free-text search');
await imagesReady();
await page.evaluate(() => window.scrollTo(0, 0));
console.log('describe', await titles(), await timing());
await shot('app-describe.png');

// 3. recipe page, picked from the describe results
const href = await page.$eval('a:has-text("See Recipe")', (a) => a.getAttribute('href'));
await open(APP + href);
await page.waitForSelector('text=More like this');
await page.waitForSelector('.shadow-xl h2');
await imagesReady();
console.log('recipe', href, await page.$eval('h1', (e) => e.textContent));
console.log('similar', await page.$$eval('.shadow-xl h2', (e) => e.map((x) => x.textContent)));
// Two tidy crops: the top of the page (times, ingredients) and the More like this row.
const card = page.locator('div.max-w-4xl');
const cb = await card.boundingBox();
const ing = await page.getByRole('heading', { name: 'Instructions' }).boundingBox();
await page.evaluate(() => window.scrollTo(0, 0));
const more = await page.getByRole('heading', { name: 'More like this' }).boundingBox();
const end = cb.y + cb.height;

await browser.close();
