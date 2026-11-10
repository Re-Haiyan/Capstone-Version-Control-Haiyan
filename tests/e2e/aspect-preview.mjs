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
      sentiment_extra: { mixed: { detected: true, probability: 0.4123, threshold: 0.3 } },
      aspect_sentiment_learned: {
        delivery: { label: 'positive', confidence: 0.7123, mention_probability: 0.8456 },
        functionality: { label: 'mixed', confidence: 0.6123, mention_probability: 0.9345 },
        quality: { label: 'neutral' }
      },
      aspect_sentiment: { version: 'aspects-cues-1', status: 'experimental', mixed_evidence: true,
        evidence: [{ aspect: 'delivery', label: 'positive', text: 'Mabilis delivery', span: [0,16], method: 'aspects-cues-1' },
          { aspect: 'functionality', label: 'negative', text: 'isang earbud lang gumagana', span: [31,57], method: 'aspects-cues-1' }] }
    } },
    { content: 'Legacy review without extras.', rating: 3, sentiment_analysis: { label: 'neutral' } },
    { content: 'Mixed detector only.', rating: 3, sentiment_analysis: {
      label: 'neutral', aspect_sentiment_learned: {},
      sentiment_extra: { mixed: { detected: false, probability: 0.8, threshold: 0.9 } }
    } },
    { content: 'Empty optional extras.', sentiment_analysis: {
      aspect_sentiment_learned: null, sentiment_extra: null
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
  assert.match(await page.locator('details[open]').innerText(), /Rule-based topic labels with exact review quotes/);
  const learned = page.getByTestId('learned-sentiment');
  assert.equal(await learned.count(), 2);
  await learned.first().locator(':scope > summary').click();
  const predictions = await learned.first().innerText();
  assert.match(predictions, /Experimental AI sentiment predictions/);
  assert.match(predictions, /Scores are not calibrated accuracy/);
  assert.match(predictions, /Mixed opinions: Predicted/);
  assert.match(predictions, /Functionality: Both positive and negative opinions/);
  assert.match(predictions, /Quality: Neutral opinion/);
  const technical = learned.first().getByTestId('learned-technical');
  assert.equal(await technical.getAttribute('open'), null);
  assert.doesNotMatch(predictions, /0\.4123|0\.7123|0\.8456|Polarity model score/);
  await technical.locator('summary').click();
  assert.notEqual(await technical.getAttribute('open'), null);
  const scores = await technical.innerText();
  assert.match(scores, /Mixed opinions model score: 0.4123/);
  assert.match(scores, /Polarity model score: 0.7123; Topic mention model score: 0.8456/);
  assert.match(scores, /Polarity model score: Unavailable/);
  assert.equal(await learned.locator('blockquote, mark').count(), 0);
  assert.doesNotMatch(predictions, /Mabilis delivery|isang earbud|threshold|%/);
  const firstReview = page.locator('#report-evidence article').first();
  assert.match(await firstReview.locator('header').innerText(), /Neutral/);
  assert.doesNotMatch(await firstReview.locator('header').innerText(), /Mixed/);
  await learned.nth(1).locator(':scope > summary').click();
  assert.match(await learned.nth(1).innerText(), /Mixed opinions: Not predicted/);
  const mixedTechnical = learned.nth(1).getByTestId('learned-technical');
  assert.equal(await mixedTechnical.getAttribute('open'), null);
  assert.doesNotMatch(await learned.nth(1).innerText(), /0\.8/);
  await mixedTechnical.locator('summary').click();
  assert.match(await mixedTechnical.innerText(), /Mixed opinions model score: 0.8/);
  const legacy = page.locator('#report-evidence article').filter({ hasText: 'Legacy review without extras.' });
  assert.equal(await legacy.locator('details').count(), 0);
  assert.match(await legacy.locator('header').innerText(), /Neutral/);
  assert.equal(await page.locator('#report-evidence article').filter({ hasText: 'Empty optional extras.' }).locator('details').count(), 0);
  assert.equal(await page.getByRole('group', { name: 'Result' }).getByText('Not enough reviews to judge').count(), 1);
  const search = page.getByRole('searchbox', { name: 'Filter reviews by word' });
  await search.fill('no-matching-review-fixture');
  await page.getByText('No reviews match these filters.', { exact: false }).waitFor();
  assert.equal(await page.locator('#report-evidence article').count(), 0);
  await page.getByRole('button', { name: 'Clear all filters', exact: true }).last().click();
  await page.locator('#report-evidence article').first().waitFor();
  assert.equal(await search.inputValue(), '');
  assert.equal(await page.locator('#report-evidence article').count(), 4);

  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.evaluate(() => {
    window.reportScrollCalls = [];
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (options) {
      window.reportScrollCalls.push({ id: this.id, behavior: options?.behavior });
      return original.call(this, options);
    };
  });
  await page.getByRole('button', { name: 'Read the reviews we have' }).click();
  await page.getByRole('button', { name: 'What do these labels mean?' }).click();
  await page.locator('#report-guide').waitFor();
  const scrolls = await page.evaluate(() => window.reportScrollCalls);
  assert.ok(scrolls.some((call) => call.id === 'report-evidence' && call.behavior === 'instant'));
  assert.ok(scrolls.some((call) => call.id === 'report-guide' && call.behavior === 'instant'));
  assert.ok(scrolls.every((call) => call.behavior !== 'smooth'));
  await page.getByRole('tab', { name: /Similar/ }).click();
  assert.equal(await page.getByRole('link', { name: 'Check another product', exact: true }).getAttribute('href'), '/scan');
  assert.deepEqual(errors, []);
  console.log('PASS: exact quotes, optional technical scores, legacy reviews, empty-filter recovery and reduced-motion scrolling');
} finally {
  await browser.close();
}
