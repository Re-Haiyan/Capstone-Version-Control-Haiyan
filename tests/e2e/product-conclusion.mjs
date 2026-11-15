// The Product Conclusion card with reasons: the lead, the counted paragraph, "Why this conclusion?" with the reviewers'
// own words, and a layout that holds on a phone, with a very long product name, and for assistive technology.
// The payloads in tests/fixtures/conclusion_cases.json are real server output (badge_view(..., aspects=True)) for
// saved products; one is a shampoo-named product whose reviews only talk about delivery and packaging.
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import { signUp } from './_signin.mjs';

const base = process.env.BASE || 'http://localhost:5173';
fs.mkdirSync('tests/e2e/shots', { recursive: true });
const axeSource = fs.readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
const cases = JSON.parse(fs.readFileSync('tests/fixtures/conclusion_cases.json', 'utf8'));
let failures = 0;
const check = (ok, what) => {
	console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
	if (!ok) failures += 1;
};

const browser = await chromium.launch({ channel: 'chrome', headless: true });
for (const width of [1280, 390, 360]) {
	const context = await browser.newContext({ viewport: { width, height: 900 } });
	await signUp(context, base);
	await context.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
	const page = await context.newPage();
	const errors = [];
	page.on('pageerror', (e) => errors.push(e.message));
	const cards = Object.values(cases).map((c) => c.card);
	await page.route('**/api/products', (r) => r.fulfill({ json: { products: cards, count: cards.length } }));
	await page.route('**/api/saved/products', (r) => r.fulfill({ json: { products: cards, count: cards.length } }));
	for (const pattern of ['**/api/products/detail**', '**/api/saved/detail**']) {
		await page.route(pattern, (r) => {
			const link = new URL(r.request().url()).searchParams.get('link');
			const found = Object.values(cases).find((c) => c.link === link);
			return found ? r.fulfill({ json: found.detail }) : r.continue();
		});
	}
	for (const [name, c] of Object.entries(cases)) {
		await page.goto(`${base}/app/report?link=${encodeURIComponent(c.link)}`, { waitUntil: 'networkidle' });
		const box = page.getByRole('group', { name: 'Result' });
		await box.waitFor({ timeout: 15000 });
		await page.waitForTimeout(1500);
		const conclusion = c.detail.product.badge_view.conclusion;
		const text = (await box.innerText()).replace(/\s+/g, ' ');
		check(text.includes(conclusion.lead), `${width}px ${name}: the lead sentence is shown`);
		check(text.includes('not independent product verification'), `${width}px ${name}: says it is not independent verification`);
		const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
		check(overflow <= 0, `${width}px ${name}: no horizontal scrolling (${overflow}px over)`);
		const boxOver = await box.evaluate((el) => el.scrollWidth - el.clientWidth);
		check(boxOver <= 0, `${width}px ${name}: the card does not overflow itself`);

		// Safety and authenticity reports: in the open (never inside a <details>), one block each, set apart from the paragraph,
		// worded as unverified reports.
		const warnings = conclusion.warnings ?? [];
		const notes = box.locator('[role="note"]');
		check((await notes.count()) === warnings.length, `${width}px ${name}: ${warnings.length} warning block(s) shown`);
		for (let i = 0; i < warnings.length; i++) {
			const note = notes.nth(i);
			check(await note.isVisible(), `${width}px ${name}: warning ${i + 1} is visible without opening anything`);
			check(await note.evaluate((el) => !el.closest('details')), `${width}px ${name}: warning ${i + 1} is not inside a collapsed section`);
			check((await note.innerText()).replace(/\s+/g, ' ').includes(warnings[i]), `${width}px ${name}: warning ${i + 1} carries the server's sentence`);
			const border = await note.evaluate((el) => getComputedStyle(el).borderLeftWidth);
			check(parseFloat(border) >= 3, `${width}px ${name}: warning ${i + 1} has a visible left bar (${border})`);
		}
		if (warnings.some((w) => /safety problem/.test(w))) {
			check(warnings.some((w) => /not been independently verified/.test(w)), `${width}px ${name}: a safety report is worded as unverified`);
		}
		check(!/\b(?:is|are) (?:dangerous|unsafe|counterfeit|fake)\b/i.test(text), `${width}px ${name}: the card never calls the product dangerous, unsafe, counterfeit or fake`);

		const why = box.getByText('Why this conclusion?');
		check((await why.count()) === 1, `${width}px ${name}: "Why this conclusion?" is offered`);
		await box.getByText('Overall assessment').scrollIntoViewIfNeeded();
		await why.click();
		const first = box.locator('details details summary').first();
		check(await first.isVisible(), `${width}px ${name}: the reasons open`);
		const items = await box.locator('section > ul > li').count();
		check(items === Math.min(8, conclusion.evidence.why.filter((w) => w.kind === 'product').length) + Math.min(8, conclusion.evidence.why.filter((w) => w.kind === 'trust').length) + Math.min(8, conclusion.evidence.why.filter((w) => w.kind === 'service').length), `${width}px ${name}: one line per counted reason (${items})`);
		await first.click();
		const quote = box.locator('details details q').first();
		check(await quote.isVisible(), `${width}px ${name}: the reviewers' own words open`);
		const shown = (await quote.innerText()).trim();
		const quoted = conclusion.evidence.why.flatMap((w) => w.quotes.map((q) => q.text));
		check(quoted.includes(shown), `${width}px ${name}: the quotation is exactly the one the server sent`);
		const after = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
		check(after <= 0, `${width}px ${name}: still no horizontal scrolling when open (${after}px over)`);
		await page.screenshot({ path: `tests/e2e/shots/conclusion-${name}-${width}.png`, fullPage: false });

		await page.waitForTimeout(1300);
		await page.evaluate(axeSource);
		const result = await page.evaluate((selector) => axe.run(document.querySelector(selector), { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } }), '[aria-label="Result"]');
		check(result.violations.length === 0, `${width}px ${name}: accessibility${result.violations.length ? ' -> ' + result.violations.map((v) => v.id + ' ' + v.nodes[0].target.join(' ')).join('; ') : ''}`);
	}
	check(errors.length === 0, `${width}px: no page errors${errors.length ? ' -> ' + errors[0] : ''}`);
	await context.close();
}
await browser.close();
console.log(failures ? `\n${failures} FAILED` : '\nall passed');
process.exit(failures ? 1 : 0);
