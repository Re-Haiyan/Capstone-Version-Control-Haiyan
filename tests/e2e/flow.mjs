// Walk the real flows against the real Flask app (its accounts go to a scratch database):
// guest is kept out -> sign up -> analyze -> report -> wishlist -> settings -> sign out -> sign in -> delete account.
import { chromium } from 'playwright-core';
import { closeTour } from './_signin.mjs';
import fs from 'node:fs';

const base = process.env.BASE || 'http://localhost:5173';
const out = 'tests/e2e/shots';
fs.mkdirSync(out, { recursive: true });
const LINK = 'https://www.lazada.com.ph/products/pdp-i5246060610-s31099995054.html';
const email = `tester${Date.now()}@example.com`;
const password = 'correct horse battery';

let failures = 0;
const check = (ok, what) => {
	console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}`);
	if (!ok) failures += 1;
};

const browser = await chromium.launch({ channel: 'chrome', headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
const problems = [];
page.on('pageerror', (e) => problems.push(`[pageerror] ${e.message}`));
page.on('response', (r) => r.status() >= 400 && problems.push(`[${r.status()}] ${r.request().method()} ${r.url().replace(base, '')}`));

// --- Guest: the app is closed, Analyze sends them to the guest screen ---------------
await page.goto(base + '/app/analyze', { waitUntil: 'networkidle' });
await page.waitForURL(base + '/scan', { timeout: 10000 });
check((await page.locator('[data-slot="sidebar"]').count()) === 0, 'guest: the Analyze address opens the guest screen, not the app');

// --- Sign up from the landing page, with mistakes, then correctly -------------------
await page.goto(base + '/', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: /Sign in/ }).first().click();
await page.getByRole('button', { name: /Sign up/ }).click();
await page.getByRole('button', { name: 'Create account' }).last().click();
await page.waitForTimeout(800);
const dialog = page.getByRole('dialog');
check((await dialog.innerText()).length > 0 && (await dialog.locator('[data-slot=field-error]').count()) > 0, 'empty sign-up shows field errors from the server');
await page.screenshot({ path: `${out}/flow_signup_errors.png` });

await dialog.getByLabel('Full name').fill('Test Shopper');
await dialog.getByLabel('Email').fill(email);
await dialog.getByLabel('Password', { exact: true }).fill(password);
await dialog.getByLabel('Confirm password').fill(password);
await dialog.getByRole('checkbox').click();
await dialog.getByRole('button', { name: 'Create account' }).click();
await page.waitForURL(/\/app\/home/, { timeout: 15000 });
check(await page.locator('[data-tour]').getByText('Welcome to DeFaketive, Test').waitFor({ timeout: 15000 }).then(() => true).catch(() => false), 'sign-up succeeds, opens the app and greets the user in the welcome tour');
await closeTour(page);
await page.waitForTimeout(800);
check(await page.getByText('Test Shopper').first().isVisible(), 'sidebar shows the account name');

// --- Analyze page -------------------------------------------------------------------
await page.goto(base + '/app/analyze', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
const primary = page.getByRole('button', { name: /^Check this product/ });
check(await primary.isDisabled(), 'empty Analyze page: main button is disabled');

await page.locator('#search-query').fill('https://example.com/not-a-shop');
check(await page.getByText('This website is not supported').isVisible(), 'unsupported link shows an error');
check(await primary.isDisabled(), 'unsupported link: button disabled');
check((await page.getByRole('button').filter({ hasText: /Search saved reports|Collect fresh reviews/ }).count()) === 0, 'one main button: no "Search saved reports" or "Collect fresh reviews"');

await page.locator('#search-query').fill(LINK);
await page.waitForTimeout(400);
check(await page.getByText('Lazada PH product link detected.').isVisible(), 'Lazada link is detected');
check(await page.getByText(/Saved report found/).isVisible(), 'saved report is found for the link');
check(await page.getByRole('button', { name: /Open report/ }).isVisible(), 'main button says "Open report"');
check(await page.getByRole('button', { name: /Check again for new reviews/ }).isVisible(), '"Check again for new reviews" is offered');
await page.screenshot({ path: `${out}/flow_analyze_match.png` });

await page.getByRole('button', { name: /Open report/ }).click();
await page.waitForURL(/\/app\/report\?link=/);
await page.getByRole('heading', { level: 2, name: /No red flags found/ }).waitFor();
check(true, 'saved report opens with its result');

// --- Save to wishlist ----------------------------------------------------------------
await page.getByRole('button', { name: /^Save$/ }).click();
await page.waitForTimeout(800);
check(await page.getByText('Saved to the wishlist in your account.').first().isVisible(), 'saving shows a toast');
const stored = await page.evaluate(() => localStorage.getItem('defaketive-wishlist'));
check(!stored, 'nothing is kept in the browser: the save went to the account');
await page.goto(base + '/app/wishlist', { waitUntil: 'networkidle' });
await page.waitForTimeout(600);
check(await page.getByText('1 product saved').isVisible(), 'wishlist shows "1 product saved"');
await page.screenshot({ path: `${out}/flow_wishlist.png`, fullPage: true });

// --- Name search: Check a product takes links; a name points to the search on Products ----------
await page.goto(base + '/app/analyze', { waitUntil: 'networkidle' });
await page.locator('#search-query').fill('cable');
check(await primary.isDisabled(), 'a plain name does not start a check');
check(!(await page.getByText('Choose a marketplace').isVisible()), 'there is no marketplace to choose (Lazada PH only)');
const toProducts = page.getByRole('link', { name: /Search Products for “cable”/ });
check(await toProducts.isVisible(), 'a plain name offers "Search Products for “cable”"');
await toProducts.click();
await page.waitForURL(/\/app\/products\?q=cable/);
await page.waitForTimeout(500);
check((await page.locator('#product-search').inputValue()) === 'cable', 'Products opens with the name in its search box');
check(await page.getByText(/product.? shown for your search/).isVisible(), 'name search lists matches on Products');
await page.getByRole('button', { name: 'Clear the search' }).click();
await page.waitForTimeout(300);
check(!(await page.getByText(/shown for your search/).isVisible()) && !new URL(page.url()).searchParams.has('q'), 'clearing the search shows everything again');

// --- Settings ----------------------------------------------------------------------
await page.goto(base + '/app/settings', { waitUntil: 'networkidle' });
await page.waitForTimeout(500);
check(await page.getByText(email).first().isVisible(), 'settings shows the account email');
await page.getByRole('button', { name: 'Edit' }).click();
await page.getByRole('dialog').getByLabel('Full name').fill('Test Shopper Renamed');
await page.getByRole('dialog').getByRole('button', { name: 'Save changes' }).click();
await page.waitForTimeout(800);
check(await page.getByRole('dialog').getByText(/current password|incorrect|required|enter/i).first().isVisible(), 'saving without the password is refused');
await page.getByRole('dialog').getByLabel('Current password').fill(password);
await page.getByRole('dialog').getByRole('button', { name: 'Save changes' }).click();
await page.getByText('Your account was updated.').first().waitFor({ timeout: 10000 });
await page.waitForTimeout(600);
check(await page.getByText('Test Shopper Renamed').first().isVisible(), 'rename shows in the page');

await page.locator('#pref-dark').click();
await page.waitForTimeout(500);
check(await page.evaluate(() => document.documentElement.classList.contains('dark')), 'dark mode switch turns the theme dark');
await page.screenshot({ path: `${out}/flow_settings_dark.png`, fullPage: true });
await page.locator('#pref-dark').click();

await page.getByRole('button', { name: 'Clear scan history' }).click();
await page.getByRole('alertdialog').getByRole('button', { name: 'Clear history' }).click();
await page.getByText('Scan history cleared. Your wishlist is kept.').first().waitFor({ timeout: 10000 });
check(true, 'clear scan history works');
await page.goto(base + '/app/history', { waitUntil: 'networkidle' });
await page.waitForTimeout(500);
check(await page.getByText('No scans yet').isVisible(), 'history is empty after clearing');
await page.screenshot({ path: `${out}/flow_history_empty.png` });
await page.goto(base + '/app/wishlist', { waitUntil: 'networkidle' });
await page.waitForTimeout(500);
check(await page.getByText('1 product saved').isVisible(), 'wishlist survives clearing history');

// --- Sign out, sign in again -------------------------------------------------------
await page.getByRole('button', { name: /Test Shopper Renamed/ }).click();
await page.getByRole('menuitem', { name: 'Sign out' }).click();
await page.waitForURL(base + '/');
await page.waitForTimeout(800);
check((await page.getByRole('button', { name: 'Sign in' }).first().isVisible()) && (await page.getByRole('dialog').count()) === 0, 'signed out back on the landing page, with no pop-up');

await page.getByRole('button', { name: 'Sign in' }).first().click();
await page.getByRole('dialog').getByLabel('Email').fill(email);
await page.getByRole('dialog').getByLabel('Password', { exact: true }).fill('wrong password here');
await page.getByRole('dialog').getByRole('button', { name: 'Sign in' }).click();
await page.getByText('Email or password is incorrect.').waitFor({ timeout: 10000 });
check(true, 'wrong password is refused with the server message');
await page.getByRole('dialog').getByLabel('Password', { exact: true }).fill(password);
await page.getByRole('dialog').getByRole('button', { name: 'Sign in' }).click();
await page.waitForURL(/\/app\/home/, { timeout: 15000 });
check(true, 'signing in from the landing page opens the app');
await page.goto(base + '/app/wishlist', { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
check(await page.getByText('1 product saved').isVisible(), 'saved wishlist comes back after signing in');

// --- Delete the account ------------------------------------------------------------
await page.goto(base + '/app/settings', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: 'Delete account' }).click();
await page.getByRole('dialog').getByLabel('Current password').fill(password);
await page.getByRole('dialog').getByRole('button', { name: 'Delete my account' }).click();
await page.waitForURL(base + '/', { timeout: 15000 });
check(true, 'deleting the account returns to the landing page');

console.log(problems.length ? `\nBrowser errors:\n  ${[...new Set(problems)].join('\n  ')}` : '\nNo browser errors.');
console.log(failures ? `\n${failures} check(s) FAILED` : '\nAll checks passed.');
await browser.close();
process.exit(failures ? 1 : 0);
