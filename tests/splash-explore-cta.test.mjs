import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const splash = readFileSync(new URL('../src/lib/components/app/splash.svelte', import.meta.url), 'utf8');

test('primary Explore action remains a real accessible button with its old destination', () => {
	assert.match(splash, /<button type="button" class="go" onclick=\{enter\} aria-label="Explore DeFaketive">/);
	assert.match(splash, /<span>Explore DeFaketive<\/span>/);
	assert.match(splash, /ArrowRightIcon class="go-arrow"/);
	assert.match(splash, /void goto\('\/enter'\)/);
	assert.match(splash, /sessionStorage\.setItem\('splash-seen', '1'\)/);
});

test('CTA dominates the product collage and is large enough for touch', () => {
	assert.match(splash, /min-height:\s*3\.75rem/);
	assert.match(splash, /min-width:\s*15rem/);
	assert.match(splash, /background:\s*var\(--mustard\)/);
	assert.match(splash, /color:\s*var\(--navy\)/);
	assert.match(splash, /box-shadow:[^\n]+rgba\(255, 255, 255/);
	assert.match(splash, /\.go:hover/);
	assert.match(splash, /\.go:focus-visible/);
	assert.match(splash, /max-width:\s*calc\(100vw - 2\.5rem\)/);
});

test('CTA still works without motion and has a mobile width', () => {
	assert.match(splash, /@media \(max-width: 480px\)/);
	assert.match(splash, /@media \(prefers-reduced-motion: reduce\)/);
	assert.match(splash, /\.go,\s*\.go-arrow\s*\{\s*transition: none/);
	assert.match(splash, /\.go,\s*\.track,/);
});
