// Browser-only fixture copied from aspect-preview.mjs; every API request is intercepted.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { chromium } from 'playwright-core';

const require = createRequire(import.meta.url);
const axeSource = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');
const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
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

const failures = [];
async function check(name, action) {
  try { await action(); console.log('PASS:', name); }
  catch (error) { failures.push(name + ': ' + error.message); console.error('FAIL:', name, error.message); }
}

async function overflow(page) {
  const result = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    width: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    offenders: [...document.querySelectorAll('body *')].filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1);
    }).slice(0, 10).map(el => el.tagName + '#' + el.id + '.' + String(el.className))
  }));
  assert.ok(result.width <= result.viewport + 1, JSON.stringify(result));
}

async function keyboardFocus(page, target) {
  await page.evaluate(() => { document.activeElement?.blur(); document.body.tabIndex = -1; document.body.focus(); });
  let reached = false;
  for (let index = 0; index < 60; index++) {
    await page.keyboard.press('Tab');
    if (await target.evaluate(el => el === document.activeElement)) { reached = true; break; }
  }
  assert.ok(reached, 'Target must be reachable with Tab');
  const visible = await target.evaluate(el => {
    if (!el.matches(':focus-visible')) return false;
    // InputGroup draws its focus ring on the wrapper using :has(:focus-visible).
    for (let node = el, depth = 0; node && depth < 3; node = node.parentElement, depth++) {
      const style = getComputedStyle(node);
      const outline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0 && style.outlineColor !== 'rgba(0, 0, 0, 0)';
      const shadow = style.boxShadow !== 'none' && !style.boxShadow.split(/,(?![^()]*\))/).every(part => part.includes('rgba(0, 0, 0, 0)'));
      if (outline || shadow) return true;
    }
    return false;
  });
  assert.ok(visible, 'Keyboard focus must have a visible outline or ring');
}

async function skipLink(page) {
  // Run immediately after navigation, before any other keyboard interaction.
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: /skip to/i });
  assert.equal(await skip.count(), 1, 'Expected one skip link');
  assert.ok(await skip.evaluate(el => el === document.activeElement), 'First Tab must focus the skip link');
  const visible = await skip.evaluate(el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.left >= 0 &&
      rect.right <= innerWidth && rect.bottom <= innerHeight &&
      style.visibility === 'visible' && Number(style.opacity) > 0 &&
      el.contains(document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2));
  });
  assert.ok(visible, 'Focused skip link must be visible inside the viewport and unobscured');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.activeElement?.matches('main#main-content'));
  assert.equal(await page.locator('main#main-content').getAttribute('tabindex'), '-1');
}

async function association(page) {
  const input = page.getByRole('textbox', { name: 'Product link', exact: true });
  assert.equal(await input.count(), 1, 'Product link must have an accessible label');
  for (const value of ['', 'not a link', product.link]) {
    await input.fill(value);
    await page.waitForTimeout(100);
    const association = await input.evaluate(el => {
      const ids = (el.getAttribute('aria-describedby') || '').trim().split(/\s+/).filter(Boolean);
      return { label: [...el.labels].some(label => label.textContent.trim()), ids,
        descriptions: ids.map(id => { const node = document.getElementById(id); return node && node.getClientRects().length ? node.textContent.trim() : ''; }),
        invalid: el.getAttribute('aria-invalid') };
    });
    assert.ok(association.label, 'Missing native label association');
    assert.ok(association.ids.length && association.descriptions.every(Boolean), 'Help/error must be associated with visible, nonempty aria-describedby targets: ' + JSON.stringify(association));
    if (value === 'not a link') {
      assert.equal(association.invalid, 'true');
      assert.match(association.descriptions.join(' '), /not a link/i);
    }
  }
  await input.fill('');
}

const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  for (const reducedMotion of ['no-preference', 'reduce']) {
    for (const width of [320, 390, 768, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, hasTouch: width <= 768, reducedMotion, serviceWorkers: 'block' });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => sessionStorage.setItem('splash-seen', '1'));
      await context.route('**/api/**', async route => {
        const path = new URL(route.request().url()).pathname;
        const json = path.endsWith('/detail') ? { product, recommendations: [] } :
          path === '/api/me' ? { user: null, guest: { limit: 3, left: 3 } } : { products: [], count: 0 };
        await route.fulfill({ json });
      });
      for (const screen of ['scan', 'report']) {
        const label = screen + ' ' + width + 'px motion=' + reducedMotion;
        await check(label + ' loaded', async () => {
          await page.goto(baseURL + (screen === 'scan' ? '/scan' : '/scan/report?link=' + encodeURIComponent(product.link)));
          await (screen === 'scan' ? page.getByRole('textbox', { name: 'Product link', exact: true }) : page.getByRole('group', { name: 'Result' })).waitFor();
          await page.evaluate(() => document.fonts.ready);
          await page.waitForTimeout(350);
        });
        await check(label + ' skip link Tab/Enter', () => skipLink(page));
        await check(label + ' no horizontal overflow', () => overflow(page));
        await check(label + ' keyboard focus', () => keyboardFocus(page, screen === 'scan' ? page.getByRole('textbox', { name: 'Product link', exact: true }) : page.getByRole('tab').first()));
        if (screen === 'scan') await check(label + ' label/help association', () => association(page));
        if (screen === 'report') {
          const tab = page.getByRole('tab').filter({ hasText: /reviews|evidence/i }).first();
          if (await tab.count()) await tab.click();
          await check(label + ' evidence overflow', () => overflow(page));
        }
        await check(label + ' axe serious/critical', async () => {
          // Measure final colors after finite entrance transitions complete naturally.
          // Do not disable animation: reduced-motion behavior is checked separately.
          await page.evaluate(async () => {
            const finite = document.getAnimations().filter(animation => {
              const timing = animation.effect.getComputedTiming();
              return timing.iterations !== Infinity && typeof timing.duration === 'number';
            });
            await Promise.all(finite.map(animation => animation.finished.catch(() => {})));
          });
          await page.addScriptTag({ content: axeSource });
          const violations = await page.evaluate(async () => (await window.axe.run(document)).violations
            .filter(issue => ['serious', 'critical'].includes(issue.impact))
            .map(issue => ({ id: issue.id, impact: issue.impact, help: issue.help, nodes: issue.nodes.map(node => ({ target: node.target, summary: node.failureSummary })) })));
          assert.deepEqual(violations, [], JSON.stringify(violations, null, 2));
        });
        if (reducedMotion === 'reduce') await check(label + ' reduced motion', async () => {
          const moving = await page.evaluate(() => {
            if (!matchMedia('(prefers-reduced-motion: reduce)').matches) return ['Media query not applied'];
            return document.getAnimations().filter(animation => {
              const timing = animation.effect.getComputedTiming();
              return animation.playState === 'running' && (timing.iterations === Infinity || Number(timing.duration) > 10);
            }).map(animation => animation.effect.target?.outerHTML.slice(0, 200));
          });
          assert.deepEqual(moving, [], 'Reduced motion leaves active animations: ' + JSON.stringify(moving));
        });
      }
      await check(width + 'px runtime errors', () => assert.deepEqual(errors, []));
      await context.close();
    }
  }
} finally { await browser.close(); }
assert.equal(failures.length, 0, failures.join('\n\n'));
console.log('PASS: responsive guest scan and synthetic report accessibility');
