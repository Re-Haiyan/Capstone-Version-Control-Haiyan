// The report: the reviewers' quotes come first, the explanations last, and there is one clear next step
// under the result for each of the four groups. Uses a made-up catalog in the browser only.
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import { signUp } from './_signin.mjs';

const base = process.env.BASE || 'http://localhost:5173';
fs.mkdirSync('tests/e2e/shots', { recursive: true });
const axeSource = fs.readFileSync('node_modules/axe-core/axe.min.js', 'utf8');
let failures = 0;
const check = (ok, what) => {
	console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
	if (!ok) failures += 1;
};

const LABELS = [
	{ category: 'safety', label: 'Safety problem', helper: 'Overheating, smoke, sparks or shocks', informs_only: false },
	{ category: 'defect', label: 'Faulty or broken', helper: "Doesn't work, stops working, drains fast or charges slowly", informs_only: false },
	{ category: 'quality', label: 'Poor quality', helper: 'Works, but weak, flimsy or scratched', informs_only: true },
	{ category: 'counterfeit', label: 'Possible fake', helper: 'Reviewers say it is a copy, not the original brand', informs_only: false },
	{ category: 'not_as_described', label: 'Not as advertised', helper: 'Size, capacity, features or looks differ from the listing', informs_only: true }
];
const TEXT = { safety: 'There is a smell on it like a burn wire.', defect: 'It stopped working after a week.' };
const SPAN = { safety: [30, 34], defect: [3, 18] };
const WORD = { safety: 'burn', defect: 'stopped working' };
// One review. `tag` is the problem it reports, if any.
const review = (i, label, tag) => ({
	author: `r${i}`, rating: label === 'positive' ? 5 : 1, time: `2026-09-${String(10 + i).padStart(2, '0')}`,
	content: tag ? `${TEXT[tag]} (${i})` : label === 'negative' ? `Not happy with this one, number ${i}.` : `Great, charges fast, number ${i}.`,
	sentiment_analysis: { label, review_tags: tag ? [tag] : [], sentences: tag ? [{ text_raw: `${TEXT[tag]} (${i})`, tags: [tag], terms: [{ span: SPAN[tag], ngram: WORD[tag], category: tag }] }] : [] }
});
// A safety review that reports a fault too, with the tags in the order the server sends them.
const both = (r) => ({ ...r, sentiment_analysis: { ...r.sentiment_analysis, review_tags: ['defect', 'safety'] } });
const badge = (category, mentions) => ({
	...LABELS.find((l) => l.category === category), mentions, reviews_analyzed: 40, phrase: 'x',
	summary: mentions ? `${mentions} review${mentions === 1 ? ' reports' : 's report'} this` : 'No reviews report this', more_evidence: 0,
	evidence: mentions && TEXT[category] ? [{ text: TEXT[category], rating: 1, highlights: [SPAN[category]] }] : []
});
const mk = (i, name, state, tone, headline, counts, comments) => ({
	name: `${name} power bank`, link: `https://www.lazada.com.ph/products/rf-${i}.html`, price: '₱499.00', rating: 4.2, platform: 'lazada', reviews_collected: comments.length, img: '',
	analysis_date: new Date(Date.now() - i * 3600000).toISOString(), comments,
	badge_view: state === 'not_analyzed'
		? { available: false, state, tone: 'unknown', headline: 'Not analyzed yet', detail: 'This product has not been checked with the current review model.', reviews_analyzed: 0, counts: { safety: 0, counterfeit: 0, defect: 0 }, badges: [], labels: LABELS }
		: { available: true, state, tone, headline, detail: `Detail for ${name}.`, reviews_analyzed: comments.length, counts: { safety: 0, defect: 0, counterfeit: 0, ...counts }, labels: LABELS, badges: LABELS.map((l) => badge(l.category, counts[l.category] ?? 0)) }
});
const fake = [
	mk(0, 'Serious', 'safety_warning', 'high', 'Reviewers report safety problems', { safety: 2 }, [review(1, 'negative', 'safety'), review(2, 'negative', 'safety'), review(3, 'positive')]),
	mk(1, 'Mild', 'possible_safety_issue', 'moderate', 'Some reviewers mention safety concerns', { safety: 1, defect: 1 }, [review(1, 'negative', 'safety'), review(2, 'negative', 'defect'), review(3, 'positive')]),
	mk(2, 'Lifted', 'no_warning_signs', 'low', 'No warning signs found', { safety: 1 }, [review(1, 'negative', 'safety'), review(2, 'positive'), review(3, 'positive')]),
	mk(3, 'Clean with a complaint', 'no_warning_signs', 'low', 'No warning signs found', { defect: 1 }, [review(1, 'negative', 'defect'), review(2, 'positive'), review(3, 'positive')]),
	mk(4, 'Clean with negatives', 'no_warning_signs', 'low', 'No warning signs found', {}, [review(1, 'negative'), review(2, 'negative'), review(3, 'positive'), review(4, 'positive')]),
	mk(5, 'Spotless', 'no_warning_signs', 'low', 'No warning signs found', {}, [review(1, 'positive'), review(2, 'positive'), review(3, 'positive')]),
	mk(6, 'Few', 'insufficient_evidence', 'unknown', 'Not enough reviews to judge', {}, [review(1, 'positive')]),
	mk(7, 'Empty', 'not_analyzed', 'unknown', '', {}, []),
	mk(8, 'Few with a complaint', 'insufficient_evidence', 'unknown', 'Not enough reviews to judge', { defect: 1 }, [review(1, 'negative', 'defect'), review(2, 'positive')]),
	// The safety review is stored last and also reports a fault; the name is as long as marketplaces write them.
	mk(9, 'Buried 20000mAh fast charging with LED display and built-in cables, model PB-2026, black, original', 'possible_safety_issue', 'moderate', 'Some reviewers mention safety concerns', { safety: 1, defect: 2 }, [review(1, 'positive'), review(2, 'negative'), review(3, 'negative', 'defect'), both(review(4, 'negative', 'safety'))])
];
// A saved report is shown as it was stored. The server says when the checker has changed since.
fake.push({ ...mk(10, 'Older', 'no_warning_signs', 'low', 'No warning signs found', {}, [review(1, 'positive'), review(2, 'positive')]), checked_with_current: false });
fake.push({ ...mk(11, 'Current', 'no_warning_signs', 'low', 'No warning signs found', {}, [review(1, 'positive'), review(2, 'positive')]), checked_with_current: true });
fake[7].checked_with_current = false; // never analysed: it already says so, no second note
// A report saved from Temu before the app became Lazada-only (14 Oct 2026): it opens, but is never checked again.
fake.push({ ...mk(12, 'Older Temu', 'no_warning_signs', 'low', 'No warning signs found', {}, [review(1, 'positive'), review(2, 'positive')]), link: 'https://www.temu.com/goods.html?goods_id=601100000000012', platform: 'temu', checked_with_current: false });
const card = ({ comments, ...rest }) => rest;
const cards = fake.map(card);
// Only "Serious" has similar products to offer.
const detailFor = (p) => ({ product: { ...p, category: 'Power banks', sentiment_summary: {} }, recommendations: p === fake[0] ? [cards[4], cards[5]] : [] });

const browser = await chromium.launch({ channel: 'chrome', headless: true });
async function open({ signedIn = true, width = 1280, height = 900, scheme = 'light' } = {}) {
	const context = await browser.newContext({ viewport: { width, height }, colorScheme: scheme });
	if (signedIn) await signUp(context, base);
	const page = await context.newPage();
	const errors = [];
	page.on('pageerror', (e) => errors.push(e.message));
	await page.route('**/api/products', (r) => r.fulfill({ json: { products: cards, count: cards.length } }));
	await page.route('**/api/saved/products', (r) => r.fulfill({ json: { products: cards, count: cards.length } }));
	for (const pattern of ['**/api/products/detail**', '**/api/saved/detail**']) {
		await page.route(pattern, (r) => {
			const p = fake.find((x) => x.link === new URL(r.request().url()).searchParams.get('link'));
			return p ? r.fulfill({ json: detailFor(p) }) : r.continue();
		});
	}
	return { context, page, errors };
}
const settle = (page, ms = 1300) => page.waitForTimeout(ms);
const url = (i, guest = false) => `${base}${guest ? '/scan' : '/app'}/report?link=${encodeURIComponent(fake[i].link)}`;
async function go(page, i, guest = false) {
	await page.goto(url(i, guest), { waitUntil: 'networkidle' });
	await page.getByRole('group', { name: 'Result' }).waitFor({ timeout: 15000 });
	await settle(page, 1500);
}
const nextSteps = async (page) => (await page.getByRole('group', { name: 'What to do next' }).getByRole('button').allInnerTexts()).map((t) => t.trim());
const selectedTab = async (page) => (await page.getByRole('tab', { selected: true }).innerText()).replace(/\s+/g, ' ').trim();
const checkedFilter = async (page) => (await page.getByRole('group', { name: 'Filter reviews' }).getByRole('radio', { checked: true }).innerText()).trim();
async function axe(page, label) {
	await page.waitForTimeout(1300);
	await page.evaluate(axeSource);
	const result = await page.evaluate(() => axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } }));
	check(result.violations.length === 0, `accessibility: ${label}${result.violations.length ? ' -> ' + result.violations.map((v) => v.id + ' ' + v.nodes[0].target.join(' ')).join('; ') : ''}`);
}

{
	const { context, page, errors } = await open();

	// ---- The order of the top of the report: name, result, next step, then the numbers ----
	await go(page, 1);
	const top = await page.evaluate(() => {
		const after = (a, b) => Boolean(a && b) && Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
		const text = (el) => el?.textContent.replace(/\s+/g, ' ').trim() ?? '';
		const name = document.querySelector('h1');
		const box = document.querySelector('[aria-label="Result"]');
		const next = document.querySelector('[aria-label="What to do next"]');
		const numbers = [...document.querySelectorAll('dl')].find((dl) => dl.textContent.includes('Report date'));
		const sample = [...document.querySelectorAll('p')].find((p) => /^We read /.test(p.textContent.trim()));
		const card = name?.closest('[data-slot="card"]');
		return {
			order: after(name, box) && after(box, next) && after(next, numbers) && after(next, sample),
			oneCard: Boolean(card) && [box, next, numbers, sample].every((el) => el?.closest('[data-slot="card"]') === card),
			beside: text(name?.parentElement),
			terms: [...(numbers?.querySelectorAll('dt') ?? [])].map(text)
		};
	});
	check(top.order && top.oneCard, 'the result comes right after the name; the next step and then the numbers follow, in one card');
	check(top.beside.includes('4.2/5') && top.beside.includes('Lazada PH · ₱499.00') && !top.beside.includes('out of 5'), `beside the name: the rating once, the marketplace and the price (${top.beside.slice(-40)})`);
	check(top.terms.join(' | ') === 'Auto-detected category | Positive reviews | Negative reviews | Flagged reviews | Report date', `under the result: ${top.terms.join(' | ')}`);

	// ---- The kinds of problem, most serious first, in two groups ----
	const groups = await page.evaluate(() => [...document.querySelectorAll('#report-findings section')].map((section) => ({
		title: section.querySelector('h3')?.textContent.trim(),
		labels: [...section.querySelectorAll('.reveal > div:first-child > span.font-medium')].map((el) => el.textContent.trim())
	})));
	check(groups.length === 2 && groups[0].title === 'Can change the result' && groups[0].labels.join(' | ') === 'Safety problem | Faulty or broken | Possible fake', `first the three that can change the result (${groups[0]?.labels.join(' | ')})`);
	check(groups[1]?.title === "Doesn't change the result" && groups[1].labels.join(' | ') === 'Poor quality | Not as advertised', `then the two that can't, under their own heading (${groups[1]?.labels.join(' | ')})`);

	// ---- The order of the first tab ----
	const titles = (await page.locator('[role="tabpanel"][data-state="active"] [data-slot="card-title"]').allInnerTexts()).map((t) => t.trim());
	check(titles[0] === 'Review sentiment', `the chart comes first (${titles[0]})`);
	check(titles[1] === 'How DeFaketive labels a product' && titles.at(-1) === 'Each check, in their own words', 'the labels sit beside the chart; the quotes from reviewers follow');
	check(!titles.includes('Why you see reviews, not a score') && !(await page.getByText('Report summary').count()), 'the "How the check works" and "Report summary" cards are gone');
	check((await page.getByRole('button', { name: 'View full detail' }).count()) === 0, 'the labels card has no full-detail dropdown');
	check(!titles.includes('What the check looks for'), 'the card that repeated the counts is gone');
	check(await page.getByText('Overheating, smoke, sparks or shocks').first().isVisible(), 'each kind of problem says what it covers');
	await page.screenshot({ path: 'tests/e2e/shots/report_flow_mild.png', fullPage: true });
	await axe(page, 'report, new order');

	// ---- Caution: read the flagged reviews; no similar products to offer ----
	let steps = await nextSteps(page);
	check(steps.join(' | ') === 'Read the 2 flagged reviews | What do these labels mean?', `Caution: next step is "${steps.join(' | ')}"`);
	check((await page.getByRole('tab', { name: /Similar/ }).innerText()).replace(/\s+/g, ' ').trim() === 'Similar products', 'the Similar tab shows no "· 0"');
	await page.getByRole('button', { name: 'Read the 2 flagged reviews' }).click();
	await settle(page, 900);
	check((await selectedTab(page)).startsWith('Reviews') && (await checkedFilter(page)).startsWith('Flagged') && (await page.getByText('Showing 2 of 2 matching reviews').isVisible()), 'it opens the Reviews tab on the 2 flagged reviews');

	// ---- "What do these labels mean?" from another tab ----
	await page.getByRole('button', { name: 'What do these labels mean?' }).click();
	await settle(page, 1200);
	const guide = await page.evaluate(() => {
		const el = document.getElementById('report-guide');
		const box = el?.getBoundingClientRect();
		return { focused: document.activeElement === el, onScreen: Boolean(box) && box.top >= 0 && box.top < innerHeight };
	});
	check((await selectedTab(page)) === 'Summary' && guide.focused && guide.onScreen, '"What do these labels mean?" goes to the explanation at the top of the first tab');

	// ---- Safety reports: flagged reviews, and similar products ----
	await go(page, 0);
	steps = await nextSteps(page);
	check(steps.join(' | ') === 'See 2 similar products with no warnings | Read the 2 flagged reviews | What do these labels mean?', `Safety reports: similar products come first, then the flagged reviews ("${steps.join(' | ')}")`);
	check((await page.getByRole('tab', { name: /Similar/ }).innerText()).replace(/\s+/g, ' ').trim() === 'Similar products · 2', 'the Similar tab shows its count when there are some');
	await page.screenshot({ path: 'tests/e2e/shots/report_flow_serious.png' });
	await page.getByRole('button', { name: 'See 2 similar products with no warnings' }).click();
	await settle(page, 900);
	check((await selectedTab(page)).startsWith('Similar') && (await page.locator('[role="tabpanel"][data-state="active"] article').count()) === 2, 'it opens the Similar tab with the 2 products');
	check((await page.locator('[role="tabpanel"][data-state="active"] article [data-slot="badge"]').first().innerText()).trim() === 'No warnings', 'each similar product carries the "No warnings" chip');

	// ---- One safety mention under a "No warning signs found" result ----
	await go(page, 2);
	const lifted = await page.evaluate(() => {
		const box = document.querySelector('[aria-label="Result"]');
		const note = [...document.querySelectorAll('p')].find((p) => p.textContent.includes('This product is shown as'));
		return { sameCard: Boolean(note) && box.closest('[data-slot="card"]') === note.closest('[data-slot="card"]'), after: Boolean(note) && Boolean(box.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING), text: note?.textContent.replace(/\s+/g, ' ').trim() ?? '' };
	});
	check(lifted.sameCard && lifted.after && /shown as Caution because 1 review mentions a safety concern/.test(lifted.text), 'the note explaining an orange "Caution" sits directly under the result');
	steps = await nextSteps(page);
	check(steps[0] === 'Read the flagged review', `Caution from one safety mention: next step is "${steps[0]}"`);
	await page.screenshot({ path: 'tests/e2e/shots/report_flow_lifted.png' });
	await axe(page, 'report with the note under the result');

	// ---- No warnings ----
	await go(page, 3);
	steps = await nextSteps(page);
	check(steps[0] === 'Read the flagged review', `No warnings, one complaint below the warning level: "${steps[0]}"`);
	await go(page, 4);
	steps = await nextSteps(page);
	check(steps[0] === 'Read the 2 negative reviews', `No warnings, nothing flagged: "${steps[0]}"`);
	await page.getByRole('button', { name: 'Read the 2 negative reviews' }).click();
	await settle(page, 900);
	check((await selectedTab(page)).startsWith('Reviews') && (await checkedFilter(page)).startsWith('Negative') && (await page.getByText('Showing 2 of 2 matching reviews').isVisible()), 'it opens the Reviews tab on the 2 negative reviews');
	await go(page, 5);
	steps = await nextSteps(page);
	check(steps[0] === 'Read all reviews', `No warnings, no negative review: "${steps[0]}"`);
	await page.getByRole('button', { name: 'Read all reviews' }).click();
	await settle(page, 900);
	check((await checkedFilter(page)).startsWith('All') && (await page.getByText('Showing 3 of 3 matching reviews').isVisible()), 'it opens every review');

	// ---- The list of reviews: most serious first, whatever order they were stored in ----
	await go(page, 9);
	await page.getByRole('tab', { name: /Reviews/ }).click();
	await settle(page, 900);
	const listed = async () => (await page.locator('[role="tabpanel"][data-state="active"] #report-evidence article').allInnerTexts()).map((t) => (t.includes('burn wire') ? 'safety' : t.includes('stopped working') ? 'defect' : 'none'));
	check((await listed()).join(' | ') === 'safety | defect', `flagged reviews: the safety report is first (${(await listed()).join(' | ')})`);
	const tags = (await page.locator('[role="tabpanel"][data-state="active"] #report-evidence article').first().locator('[data-slot="badge"]').allInnerTexts()).map((t) => t.trim());
	check(tags.includes('Faulty or broken') && tags.indexOf('Safety problem') >= 0 && tags.indexOf('Safety problem') < tags.indexOf('Faulty or broken'), `a review with two tags shows the more serious one first (${tags.join(' | ')})`);
	await page.getByRole('group', { name: 'Filter reviews' }).getByRole('radio', { name: /^All/ }).click();
	await settle(page, 600);
	check((await listed()).join(' | ') === 'safety | defect | none | none', `all reviews: reported problems first (${(await listed()).join(' | ')})`);
	check(await page.getByText('Showing 4 of 4 matching reviews, most serious first.').isVisible(), 'the list says it is sorted "most serious first"');
	await page.getByRole('group', { name: 'Filter reviews' }).getByRole('radio', { name: /^Positive/ }).click();
	await settle(page, 600);
	check(await page.getByText('Showing 1 of 1 matching review.').isVisible(), 'a list with nothing to sort does not claim an order');

	// ---- No result yet ----
	await go(page, 6);
	steps = await nextSteps(page);
	check(steps[0] === 'Read the reviews we have', `No result yet: "${steps[0]}"`);
	await go(page, 8);
	steps = await nextSteps(page);
	check(steps[0] === 'Read the flagged review', `No result yet, but one review reports a problem: "${steps[0]}"`);
	await go(page, 7);
	steps = await nextSteps(page);
	check(steps.join(' | ') === 'What do these labels mean?', 'No result yet and no stored reviews: only the labels link, no dead button');
	check((await page.locator('[data-behind-checker]').count()) === 0, 'a product that was never analysed gets no "earlier checker" note on top of "Not analyzed yet"');

	// ---- A report made by an earlier version of the checker ----
	await go(page, 10);
	const older = await page.evaluate(() => {
		const after = (a, b) => Boolean(a && b) && Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
		const note = document.querySelector('[data-behind-checker]');
		return {
			text: note?.textContent.replace(/\s+/g, ' ').trim() ?? '',
			href: note?.querySelector('a')?.getAttribute('href') ?? '',
			placed: after(document.querySelector('[aria-label="Result"]'), note) && after(note, document.querySelector('[aria-label="What to do next"]'))
		};
	});
	check(older.text === 'This report was made with an earlier version of the checker. Check it again to bring it up to date.', `an older report says so (${older.text})`);
	check(older.placed, 'the note sits under the result, before the next step');
	check(older.href === `/app/analyze?q=${encodeURIComponent(fake[10].link)}`, `"Check it again" leads to the check page with the link kept (${older.href})`);
	await axe(page, 'report made by an earlier checker');
	await go(page, 12);
	const temu = await page.evaluate(() => {
		const note = document.querySelector('[data-behind-checker]');
		return { text: note?.textContent.replace(/\s+/g, ' ').trim() ?? '', links: note?.querySelectorAll('a').length ?? -1 };
	});
	check(temu.text === "This report was made with an earlier version of the checker. It can't be checked again: DeFaketive now checks Lazada PH products only." && temu.links === 0, `an older Temu report opens but offers no new check (${temu.text})`);
	await go(page, 11);
	check((await page.locator('[data-behind-checker]').count()) === 0, 'a report from the current checker has no note');
	await go(page, 5);
	check((await page.locator('[data-behind-checker]').count()) === 0, 'a server that does not say (the plain original app) counts as up to date');
	check(errors.length === 0, `no browser errors${errors.length ? ': ' + errors[0] : ''}`);
	await context.close();
}

// ---- The guest report is the same component ----
{
	const { context, page } = await open({ signedIn: false });
	await go(page, 0, true);
	const steps = await nextSteps(page);
	check(steps[0] === 'See 2 similar products with no warnings' && steps[1] === 'Read the 2 flagged reviews', 'guest report: the same next steps');
	await page.getByRole('button', { name: 'See 2 similar products with no warnings' }).click();
	await settle(page, 900);
	const href = await page.locator('[role="tabpanel"][data-state="active"] article a', { hasText: 'Open report' }).first().getAttribute('href');
	check(/^\/scan\/report\?link=/.test(href ?? ''), 'guest report: similar products open on the guest screen');
	await context.close();
}

// ---- Dark, and a phone ----
{
	const { context, page } = await open({ scheme: 'dark' });
	await go(page, 0);
	await axe(page, 'report, dark');
	await page.screenshot({ path: 'tests/e2e/shots/report_flow_dark.png' });
	await context.close();
}
{
	const { context, page } = await open({ width: 390, height: 844 });
	for (const i of [0, 2, 7]) {
		await go(page, i);
		check((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 1, `phone: report "${fake[i].name.replace(' power bank', '')}" does not scroll sideways`);
	}
	// On a phone the result must not need scrolling, even under a long product name.
	for (const i of [0, 9]) {
		await go(page, i);
		const box = await page.evaluate(() => {
			const r = document.querySelector('[aria-label="Result"]').getBoundingClientRect();
			return { top: Math.round(r.top), bottom: Math.round(r.bottom), screen: innerHeight, sideways: document.documentElement.scrollWidth - innerWidth };
		});
		check(box.top > 0 && box.bottom <= box.screen && box.sideways <= 1, `phone: the whole result is on the first screen${i === 9 ? ', under a long name too' : ''} (${box.top} to ${box.bottom} of ${box.screen})`);
		await page.screenshot({ path: `tests/e2e/shots/report_flow_phone_first_screen_${i}.png` });
	}
	await go(page, 0);
	await page.screenshot({ path: 'tests/e2e/shots/report_flow_phone.png', fullPage: true });
	await context.close();
}

await browser.close();
console.log(failures ? `\n${failures} check(s) FAILED` : '\nAll checks passed.');
process.exit(failures ? 1 : 0);
