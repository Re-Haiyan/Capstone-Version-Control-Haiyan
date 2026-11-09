// Synthetic browser-only fixture; does not insert accounts or saved reports.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage();
  await page.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const content = 'Mabilis delivery at mura, pero isang earbud lang gumagana.';
  const product = {
    link: 'https://www.lazada.com.ph/products/aspect-preview.html', name: 'Aspect preview fixture',
    platform: 'lazada', checked_with_current: true, sentiment_summary: {},
    badge_view: { available: true, state: 'insufficient_evidence', tone: 'unknown',
      headline: 'Not enough reviews to judge', detail: 'Browser-only fixture', reviews_analyzed: 1,
      counts: {}, badges: [], labels: [] },
    comments: [{ content, rating: 3, sentiment_analysis: {
      label: 'neutral', review_tags: [], sentences: [],
      aspect_sentiment: { version: 'aspects-cues-1', status: 'experimental', mixed_evidence: true,
        evidence: [{ aspect: 'delivery', label: 'positive', text: 'Mabilis delivery', span: [0,16], method: 'aspects-cues-1' },
          { aspect: 'functionality', label: 'negative', text: 'isang earbud lang gumagana', span: [31,57], method: 'aspects-cues-1' }] }
    } }]
  };
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = path.endsWith('/detail') ? { product, recommendations: [] } :
      path === '/api/me' ? { user: null, guest: { limit: 3, left: 3 } } : { products: [], count: 0 };
    await route.fulfill({ json });
  });
  await page.goto(`http://localhost:5173/scan/report?link=${encodeURIComponent(product.link)}`);
  const summary = page.locator('summary').filter({ hasText: 'Opinions by topic' });
  // Some report layouts initially show a different tab.
  await page.getByRole('group', { name: 'Result' }).waitFor();
  const tab = page.getByRole('tab').filter({ hasText: /reviews|evidence/i }).first();
  if (await tab.count()) await tab.click();
  await summary.waitFor({ timeout: 15000 });
  await summary.click();
  assert.match(await page.locator('details[open]').innerText(), /Functionality: negative/);
  assert.equal(await page.locator('details[open] mark').first().innerText(), 'Mabilis delivery');
  assert.deepEqual(errors, []);
  console.log('PASS: aspect preview, evidence text and mixed-opinion indicator render without browser errors');
} finally {
  await browser.close();
}
