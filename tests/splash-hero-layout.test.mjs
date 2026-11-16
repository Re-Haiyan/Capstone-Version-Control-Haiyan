import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const splash = readFileSync(new URL('../src/lib/components/app/splash.svelte', import.meta.url), 'utf8');

test('brand welcome page explains its purpose before the primary action', () => {
	const title = splash.indexOf('id="splash-title"');
	const description = splash.indexOf('id="splash-description"');
	const cta = splash.indexOf('<button type="button" class="go"');
	assert.ok(title > 0);
	assert.ok(description > title, 'a short explanation should follow the heading');
	assert.ok(cta > description, 'one clear CTA should follow the explanation');
	assert.match(splash, /Know what buyers really say before you buy/);
	assert.match(splash, /what went wrong, and possible safety concerns/);
	assert.match(splash, /Review-based guidance, not independent product testing/);
});

test('a soft central panel separates text from the collage without deleting the imagery', () => {
	assert.match(splash, /class="collage" aria-hidden="true"/);
	assert.match(splash, /<section class="stack" aria-labelledby="splash-title">/);
	assert.match(splash, /width: min\(36rem, 100%\)/);
	assert.match(splash, /background: rgba\(255, 255, 255, 0\.94\)/);
	assert.match(splash, /border-top: 4px solid var\(--mustard\)/);
	assert.match(splash, /backdrop-filter: blur\(14px\)/);
	assert.match(splash, /<h1 id="splash-title" class="hero-title">/);
	assert.match(splash, /font: 800 clamp\(1\.4rem/);
});

test('modal keyboard access and small-screen viewing remain usable', () => {
	assert.match(splash, /role="dialog" aria-modal="true" aria-labelledby="splash-title" aria-describedby="splash-description"/);
	assert.match(splash, /bind:this=\{exploreButton\}/);
	assert.match(splash, /focus\(\{ preventScroll: true \}\)/);
	assert.match(splash, /event\.key === 'Tab'/);
	assert.match(splash, /overflow-y: auto/);
	assert.match(splash, /@media \(max-width: 480px\)/);
	assert.match(splash, /@media \(max-height: 650px\)/);
	assert.match(splash, /@media \(prefers-reduced-motion: reduce\)/);
	assert.match(splash, /void goto\('\/enter'\)/);
});

test('entry, session behavior and source brand logo are unchanged', () => {
	assert.match(splash, /import logo from '#lib\/assets\/logo\.png'/);
	assert.match(splash, /sessionStorage\.setItem\('splash-seen', '1'\)/);
	assert.match(splash, /sessionStorage\.getItem\('splash-seen'\)/);
	assert.match(splash, /<span>Explore DeFaketive<\/span>/);
});
