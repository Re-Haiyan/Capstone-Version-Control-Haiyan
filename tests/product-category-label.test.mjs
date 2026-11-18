import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { categoryForReport } from '../src/lib/product-category-label.js';

const component = readFileSync(
	new URL('../src/lib/components/report/verdict-block.svelte', import.meta.url), 'utf8'
);
const report = readFileSync(
	new URL('../src/lib/components/report/report-view.svelte', import.meta.url), 'utf8'
);

test('the conclusion shows backend-recorded product categories as small readable labels', () => {
	const category = categoryForReport({ product_category: 'battery_solar', checked_with_current: true });
	assert.deepEqual(
		{ label: category.label, stale: category.stale },
		{ label: 'Battery & Solar', stale: false }
	);
	assert.match(category.explanation, /listing title/);
	assert.equal(categoryForReport({ product_category: 'tv_display' }).label, 'TV & Display');
	assert.equal(categoryForReport({ product_category: 'health_supplements' }).label, 'Health Supplements');
	assert.equal(categoryForReport({ product_category: 'home_textile' }).label, 'Home Textile');
	assert.equal(categoryForReport({ product_category: 'gaming' }).label, 'Gaming');
});

test('unknown categories, old saved reports, and missing metadata are transparent', () => {
	assert.equal(categoryForReport({ product_category: 'other' }).label, 'Unclassified');
	assert.equal(categoryForReport({}).label, 'Not recorded');
	assert.equal(categoryForReport(null).label, 'Not recorded');
	assert.equal(categoryForReport({ product_category: 'INVALID / category' }).label, 'Unclassified');
	const previous = categoryForReport({ product_category: 'gaming', checked_with_current: false });
	assert.equal(previous.label, 'Gaming');
	assert.equal(previous.stale, true);
	assert.match(previous.explanation, /earlier checker/);
	assert.equal(categoryForReport({ checked_with_current: false }).stale, true);
});

test('category pill belongs inside the conclusion card, not the report metric grid', () => {
	assert.match(component, /categoryForReport\(product\)/);
	assert.match(component, /data-product-category/);
	assert.match(component, /Category:/);
	assert.match(component, /\{detectedCategory\.label\}/);
	assert.match(component, /\{#if detectedCategory\.stale\}/);
	assert.match(component, /\(earlier report\)/);
	assert.ok(component.indexOf('data-product-category') < component.indexOf('What reviewers liked'));
	assert.doesNotMatch(report, /\['Auto-detected category'/);
});

test('category stays display-only; checker decisions and warning information remain independent', () => {
	assert.match(component, /const verdict = \$derived\(view\(product\)\)/);
	assert.match(component, /reviewRecommendation\(product\)/);
	assert.match(component, /Common concerns/);
	assert.doesNotMatch(component, /product\.product_category\s*=/);
	assert.doesNotMatch(component, /sentiment_analysis\s*=/);
});
