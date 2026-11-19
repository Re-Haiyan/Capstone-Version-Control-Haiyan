// Fixture-only served acceptance. Never creates accounts or scans on production.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
import { signUp } from './_signin.mjs';

const base = process.env.DEFAKETIVE_ACCEPTANCE_URL;
if (!base || !['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) {
	throw new Error('Set DEFAKETIVE_ACCEPTANCE_URL to the isolated fixture server on loopback.');
}
const cards = (await (await fetch(base + '/api/saved/products')).json()).products;
assert.equal(cards.length, 51, 'requires the isolated 49-category + hazard + empty fixture inventory');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
	const context = await browser.newContext({ viewport: { width: 1365, height: 1000 } });
	await signUp(context, base, 'Acceptance Shopper');
	await context.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
	const page = await context.newPage();
	let visited = 0;
	for (const card of cards) {
		await page.goto(base + '/app/products', { waitUntil: 'networkidle' });
		const tour = page.locator('[data-tour]');
		if (await tour.isVisible()) await tour.getByRole('button', { name: 'Skip', exact: true }).click();
		await page.getByLabel('Search by name', { exact: true }).fill(card.name);
		await page.getByRole('link', { name: card.name, exact: true }).first().click();
		await page.getByRole('heading', { name: card.name, exact: true }).waitFor();
		await page.getByRole('group', { name: 'Product review result', exact: true }).waitFor();
		if (card.name === 'Acceptance Phone Charger Positive Hazard') {
			assert.match(await page.locator('main').innerText(), /possible safety concern|safety concern/i);
			await page.getByRole('button', { name: 'Read the flagged review', exact: true }).click();
			await page.locator('[data-review-stages] summary').click();
			assert.match(await page.locator('[data-review-stages]').innerText(), /Initial model sentiment: positive/);
			assert.match(await page.getByRole('tabpanel', { name: 'Reviews' }).innerText(), /cable sparked once/);
			assert.match(await page.locator('main').innerText(), /Review-reported signals/);
			const [download] = await Promise.all([
				page.waitForEvent('download'), page.getByRole('button', { name: 'Download report', exact: true }).click()
			]);
			const stream = await download.createReadStream();
			const chunks = [];
			for await (const chunk of stream) chunks.push(chunk);
			const saved = JSON.parse(Buffer.concat(chunks).toString()).product;
			assert.equal(saved.comments[0].sentiment_analysis.sentiment.initial_label, 'positive');
			assert.ok(saved.comments[0].sentiment_analysis.review_tags.includes('safety'));
			assert.ok(saved.comments[0].sentiment_analysis.review_evidence.safety.spans.length);
			await page.getByRole('button', { name: 'How was this result reached?', exact: true }).click();
			assert.equal(await page.getByRole('list', { name: 'Five stages of the product review analysis' }).locator('li').count(), 5);
			await page.keyboard.press('Escape');
		} else if (card.name === 'Acceptance Empty Charger') {
			assert.match(await page.getByRole('group', { name: 'Product review result' }).innerText(), /not enough|limited|too few/i);
		}
		visited++;
	}
	await page.goto(base + '/app/analyze', { waitUntil: 'networkidle' });
	await page.getByLabel('Product link', { exact: true }).fill('https://www.lazada.com.ph/shop-mobiles/');
	assert.ok(await page.getByRole('button', { name: 'Check this Lazada PH category', exact: true }).isEnabled());
	console.log(JSON.stringify({ passed: true, grid_selections: visited, named_categories: 49,
		positive_hazard: true, zero_reviews: true, download_evidence: true, category_url_control: true }));
} finally { await browser.close(); }
