import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const report = readFileSync(new URL('../src/lib/components/report/report-view.svelte', import.meta.url), 'utf8');

test('product category is not shown as a shopper-facing report metric', () => {
	assert.doesNotMatch(report, /Auto-detected category/i);
	assert.doesNotMatch(report, /detectedCategory/);
	for (const label of ['Positive reviews', 'Negative reviews', 'Flagged reviews', 'Report date']) {
		assert.ok(report.includes("['" + label + "'"), label + ' should remain visible');
	}
	assert.match(report, /#each details as \[term, value\]/);
});

test('category remains available in the backend, rather than being deleted from product data', () => {
	const productTypes = readFileSync(new URL('../src/lib/types.ts', import.meta.url), 'utf8');
	assert.match(productTypes, /product_category\?: string/);
});
