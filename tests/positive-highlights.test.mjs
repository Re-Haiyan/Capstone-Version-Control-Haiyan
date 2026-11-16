import assert from 'node:assert/strict';
import { test } from 'node:test';
import { positiveHighlights, reviewMentionCount } from '../src/lib/positive-highlights.js';

const make = (rows, reviewed = 35) => ({ evidence: { reviews_considered: reviewed, why: rows } });
const why = (aspect, kind, polarity, reviews, quote = 'Actual shopper comment.') => ({
	aspect, kind, polarity, reviews,
	text: aspect + ': ' + reviews + ' reviews supporting',
	quotes: [{ text: quote }],
	review_ids: Array.from({ length: reviews }, (_, i) => String(i)),
});

test('ranks and limits backed positive product themes by distinct review counts', () => {
	const result = positiveHighlights(make([
		why('Comfort', 'product', 'positive', 8),
		why('Battery life', 'product', 'positive', 4),
		why('Value for money', 'product', 'positive', 6),
		why('Appearance', 'product', 'positive', 2),
		why('Performance', 'product', 'positive', 1)
	]), 3);
	assert.deepEqual(result.product.map((r) => r.label), ['Comfort', 'Value for money', 'Battery life']);
	assert.deepEqual(result.product.map((r) => r.reviews), [8, 6, 4]);
	assert.equal(result.reviewed, 35);
	assert.equal(result.available, true);
	assert.equal(result.product[0].quotes[0], 'Actual shopper comment.');
});

test('does not promote mixed-negative aspects or counterfeit claims as product praise', () => {
	const result = positiveHighlights(make([
		why('Build quality', 'product', 'positive', 4),
		why('Build quality', 'product', 'negative', 5),
		why('Authenticity', 'trust', 'positive', 12),
		why('Size', 'product', 'positive', 3),
		why('Size', 'product', 'negative', 1)
	]));
	assert.deepEqual(result.product.map((r) => r.label), ['Size']);
	assert.equal(result.product[0].concerns, 1);
});

test('separates delivery-only praise from product qualities', () => {
	const result = positiveHighlights(make([why('Fast delivery', 'service', 'positive', 22)]));
	assert.deepEqual(result.product, []);
	assert.equal(result.service[0].reviews, 22);
});

test('does not invent keywords if the record has no backend evidence', () => {
	assert.deepEqual(positiveHighlights(null), { product: [], service: [], reviewed: 0, available: false });
	assert.deepEqual(positiveHighlights({ headline: 'Highly rated', assessment: 'Well reviewed' }).product, []);
	assert.deepEqual(positiveHighlights(make([why('Warranty', 'product', 'negative', 3)])).product, []);
});

test('drops invalid or empty labels and shows grammatically correct counts', () => {
	const result = positiveHighlights(make([
		{ ...why('Comfort', 'product', 'positive', 3), text: ': 3 reviews supporting' },
		{ ...why('Price', 'product', 'positive', 2), reviews: 1.5 },
		{ ...why('Color', 'product', 'positive', 0) },
		why('Portability', 'product', 'positive', 1)
	]));
	assert.deepEqual(result.product.map((r) => r.label), ['Portability']);
	assert.equal(reviewMentionCount(1), '1 review');
	assert.equal(reviewMentionCount(2), '2 reviews');
});
