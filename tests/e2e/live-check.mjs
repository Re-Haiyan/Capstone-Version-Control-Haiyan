// Read-only browser check of REAL saved reports on a running site (default: the public site). Guest only: no sign-up, no clicks that change data.
//   BASE=https://defaketive.duckdns.org PICK=pick.json OUT=live_browser.json node tests/e2e/live-check.mjs
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const base = process.env.BASE || 'https://defaketive.duckdns.org';
const picks = JSON.parse(fs.readFileSync(process.env.PICK, 'utf8'));
const results = [];
const browser = await chromium.launch({ channel: 'chrome', headless: true });
for (const width of [1280, 390, 360]) {
	const context = await browser.newContext({ viewport: { width, height: 900 } });
	await context.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
	const page = await context.newPage();
	const consoleErrors = [];
	const failedApi = [];
	page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + e.message));
	page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push('console: ' + m.text().slice(0, 160)); });
	page.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 400) failedApi.push(`${r.status()} ${new URL(r.url()).pathname}`); });
	for (const p of picks) {
		consoleErrors.length = 0; failedApi.length = 0;
		const entry = { width, name: p.name, state: p.state, decision: p.decision };
		try {
			await page.goto(`${base}/scan/report?link=${encodeURIComponent(p.link)}`, { waitUntil: 'networkidle', timeout: 45000 });
			const box = page.getByRole('group', { name: 'Result' });
			await box.waitFor({ timeout: 20000 });
			await page.waitForTimeout(1200);
			entry.text = (await box.innerText()).replace(/\s+/g, ' ');
			entry.overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
			entry.warningBlocks = await box.locator('[role="note"]').count();
			const why = box.locator('details', { hasText: 'Why this conclusion?' });
			entry.hasWhy = (await why.count()) > 0;
			if (entry.hasWhy) {
				await why.first().locator('summary').click();
				entry.whyText = (await why.first().innerText()).replace(/\s+/g, ' ').slice(0, 1500);
			}
		} catch (e) {
			entry.error = String(e.message).slice(0, 200);
		}
		entry.consoleErrors = [...consoleErrors];
		entry.failedApi = [...failedApi];
		results.push(entry);
	}
	await context.close();
}
await browser.close();
fs.writeFileSync(process.env.OUT || 'live_browser.json', JSON.stringify(results, null, 1));
const bad = results.filter((r) => r.error || r.consoleErrors.length || r.failedApi.length || r.overflow > 0);
console.log(`${results.length} page views; ${bad.length} with an error, console error, failed API call or horizontal overflow`);
for (const r of bad.slice(0, 8)) console.log(' ', r.width, r.name?.slice(0, 40), r.error || r.consoleErrors[0] || r.failedApi[0] || `overflow ${r.overflow}px`);
