// Browser-only synthetic API fixture. Run with Vite on 5173: node tests/e2e/mobile-menu.mjs
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';

const base = process.env.E2E_BASE_URL || process.env.BASE || 'http://localhost:5173';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const errors = [];

async function fixture(width, role = 'guest') {
  const context = await browser.newContext({ viewport: { width, height: 844 } });
  await context.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
  let signedIn = role !== 'guest';
  const logouts = [];
  await context.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/logout')) {
      logouts.push({ path, method: route.request().method() });
      signedIn = false;
    }
    const account = { id: 123, name: 'Menu Tester', email: 'menu@example.test', role: 'admin' };
    const json = path.startsWith('/api/admin/') ? { admin: signedIn && role === 'admin' ? account : null } :
      path.startsWith('/api/auth/') ? { user: signedIn && role === 'user' ? account : null, guest: { limit: 3, left: 3 } } :
      { products: [], count: 0 };
    await route.fulfill({ json });
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  const trigger = page.getByRole('button', { name: 'Open navigation menu', exact: true });
  const menu = page.getByRole('dialog', { name: 'Menu', exact: true });
  return { context, page, trigger, menu, logouts };
}

async function keyboardOpen(page, trigger, menu) {
  let reached = false;
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press('Tab');
    if (await trigger.evaluate(el => el === document.activeElement)) { reached = true; break; }
  }
  assert.ok(reached, 'Menu trigger is reachable with Tab');
  await page.keyboard.press('Enter');
  await menu.waitFor();
  assert.equal(await trigger.getAttribute('aria-expanded'), 'true');
}

try {
  for (const width of [320, 390]) {
    const { context, page, trigger, menu } = await fixture(width);
    await trigger.waitFor();
    assert.equal(await page.locator('header').getByRole('button', { name: 'Sign in', exact: true }).isVisible(), false);
    await keyboardOpen(page, trigger, menu);
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab');
      assert.ok(await menu.evaluate(el => el.contains(document.activeElement)), 'Tab focus stays in the sheet');
    }
    await page.keyboard.press('Escape');
    await menu.waitFor({ state: 'hidden' });
    await page.waitForFunction(() => document.activeElement?.getAttribute('aria-label') === 'Open navigation menu');
    assert.equal(await trigger.getAttribute('aria-expanded'), 'false');
    for (const [name, hash] of [['How it works', '#how'], ['FAQ', '#faq'], ['About', '#about']]) {
      await trigger.click();
      const link = menu.getByRole('link', { name, exact: true });
      assert.equal(await link.getAttribute('href'), '/' + hash);
      await link.click();
      await menu.waitFor({ state: 'hidden' });
      await page.waitForURL(url => url.hash === hash);
    }
    await trigger.click();
    const dark = await page.locator('html').evaluate(el => el.classList.contains('dark'));
    await menu.getByRole('button', { name: 'Switch between light and dark theme' }).click();
    await page.waitForFunction(previous => document.documentElement.classList.contains('dark') !== previous, dark);
    assert.ok(await menu.isVisible(), 'Changing theme keeps menu open');
    for (const action of ['Sign in', 'Create account']) {
      if (!(await menu.isVisible())) await trigger.click();
      await menu.getByRole('button', { name: action, exact: true }).click();
      await menu.waitFor({ state: 'hidden' });
      const auth = page.getByRole('dialog').filter({ has: page.getByRole('textbox', { name: /email/i }) });
      await auth.waitFor();
      assert.ok(await auth.getByRole('button', { name: action, exact: true }).isVisible());
      await page.keyboard.press('Escape');
      await auth.waitFor({ state: 'hidden' });
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow');
    console.log(`PASS ${width}px: navigation, theme, guest actions, keyboard trap, Escape and focus return`);
    await context.close();

    for (const role of ['user', 'admin']) {
      const fixtureResult = await fixture(width, role);
      const { page, trigger, menu, context, logouts } = fixtureResult;
      await trigger.click();
      await menu.getByText('Hi, Menu').waitFor();
      assert.ok(await menu.getByRole('link', { name: role === 'admin' ? 'Admin' : 'Open app', exact: true }).isVisible());
      await menu.getByRole('button', { name: 'Sign out', exact: true }).click();
      await menu.waitFor({ state: 'hidden' });
      await trigger.click();
      await menu.getByRole('button', { name: 'Sign in', exact: true }).waitFor();
      assert.deepEqual(logouts, [{ path: `/api/${role === 'admin' ? 'admin' : 'auth'}/logout`, method: 'POST' }]);
      console.log(`PASS ${width}px: ${role} account action and synthetic sign-out`);
      await context.close();
    }
  }
  const { context, page, trigger } = await fixture(1280);
  await page.getByRole('navigation', { name: 'Main navigation', exact: true }).waitFor();
  assert.equal(await trigger.isVisible(), false, 'Mobile trigger hidden on desktop');
  for (const name of ['How it works', 'FAQ', 'About']) {
    assert.ok(await page.getByRole('navigation', { name: 'Main navigation', exact: true }).getByRole('link', { name, exact: true }).isVisible());
  }
  assert.deepEqual(errors, []);
  console.log('PASS desktop navigation preserved, mobile trigger hidden, no browser errors');
  await context.close();
} finally {
  await browser.close();
}
