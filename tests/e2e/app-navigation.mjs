// Synthetic signed-in layout check; no live account or database writes.
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  for (const width of [320, 390, 768, 1280]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, hasTouch: width < 768 });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
    await context.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname;
      return route.fulfill({ json: path === '/api/auth/me'
        ? { user: { id: 42, name: 'Test Shopper', email: 'test@example.invalid' } }
        : { products: [], count: 0, activity: [], wishlist: [] } });
    });
    await page.goto((process.env.E2E_BASE_URL || 'http://127.0.0.1:5173') + '/app/about');
    const nav = page.getByRole('navigation', { name: 'Main', exact: true });
    await nav.waitFor();
    await page.evaluate(() => document.fonts.ready);
    const links = nav.getByRole('link');
    assert.equal(await links.count(), width < 768 ? 4 : 7);
    if (width < 768) {
      assert.deepEqual(await links.allTextContents().then(labels => labels.map(label => label.trim())), ['Home', 'Check', 'Products', 'Saved']);
      const more = nav.getByRole('button', { name: 'More navigation' });
      await more.focus();
      await page.keyboard.press('Enter');
      const menu = page.getByRole('menu');
      await menu.waitFor();
      for (const name of ['History', 'About', 'FAQ']) {
        const item = menu.getByRole('menuitem', { name, exact: true });
        assert.ok(await item.isVisible());
        assert.equal(await item.getAttribute('href'), '/app/' + name.toLowerCase());
      }
      assert.equal(await menu.getByRole('menuitem', { name: 'About', exact: true }).getAttribute('aria-current'), 'page');
      await page.keyboard.press('Escape');
      await menu.waitFor({ state: 'hidden' });
      assert.ok(await more.evaluate(el => el === document.activeElement));
      await more.click();
      await page.getByRole('menuitem', { name: 'FAQ', exact: true }).click();
      await page.waitForURL('**/app/faq');
      await menu.waitFor({ state: 'hidden' });
    } else {
      assert.equal(await page.getByRole('button', { name: 'More navigation' }).isVisible(), false);
    }
    const labels = await links.evaluateAll(items => items.map(link => {
      const text = link.lastElementChild;
      const box = text.getBoundingClientRect();
      const parent = link.getBoundingClientRect();
      return { text: text.textContent, size: parseFloat(getComputedStyle(text).fontSize),
        fits: box.left >= parent.left - 1 && box.right <= parent.right + 1 };
    }));
    assert.ok(labels.every(label => label.size >= 12 && label.fits), JSON.stringify(labels));
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.deepEqual(errors, []);
    console.log(`PASS: signed-in navigation ${width}px`);
    await context.close();
  }
} finally { await browser.close(); }
