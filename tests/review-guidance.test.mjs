import assert from 'node:assert/strict';
import { test } from 'node:test';
import { reviewGuidance } from '../src/lib/review-guidance.js';

const aspect = (aspect, reviews, polarity = 'positive', kind = 'product') => ({
	kind, aspect, polarity, reviews,
	text: aspect + ': ' + reviews + ' reviews supporting',
	quotes: [{ text: 'A fictional review praising ' + aspect }]
});
const product = ({
	analyzed = 93,
	tone = 'low',
	available = true,
	positive = 68,
	negative = 15,
	uncertain = 10,
	rows = [
		aspect('Value for money', 6),
		aspect('Fit and sizing', 3),
		aspect('Comfort', 2),
		aspect('Delivery', 9, 'positive', 'service')
	],
	badges = [],
	counts = {}
} = {}) => ({
	sentiment_summary: {
		sentiment_counts: { positive, negative, uncertain }
	},
	badge_view: {
		available, reviews_analyzed: analyzed, tone, badges, counts,
		conclusion: { evidence: { reviews_considered: analyzed, why: rows } }
	}
});

test('93-review summary names only supported positive qualities and their exact counts', () => {
	const result = reviewGuidance(product());
	assert.equal(result.analyzed, 93);
	assert.equal(result.safety, false);
	assert.match(result.text, /^According to 93 analyzed customer reviews/);
	assert.match(result.text, /value for money \(6 reviews\)/);
	assert.match(result.text, /fit and sizing \(3 reviews\)/);
	assert.match(result.text, /comfort \(2 reviews\)/);
	assert.match(result.text, /may appeal to shoppers who prioritize/);
	assert.doesNotMatch(result.text, /delivery|safe to buy|guaranteed/i);
});

test('355-review safety report never recommends or asserts suitable', () => {
	const r = reviewGuidance(product({
		analyzed: 355,
		tone: 'moderate',
		positive: 138,
		negative: 178,
		uncertain: 39,
		badges: [{ category: 'safety', label: 'Safety problem', mentions: 3 }]
	}));
	assert.equal(r.safety, true);
	assert.match(r.text, /355 analyzed customer reviews/);
	assert.match(r.text, /3 reviews mention a possible safety concern/);
	assert.doesNotMatch(r.text, /may appeal|safe to buy|recommend buying/i);
});

test('one safety report also overrides a positive majority', () => {
	const r = reviewGuidance(product({ counts: { safety: 1 } }));
	assert.equal(r.safety, true);
	assert.match(r.text, /1 review mentions a possible safety concern/);
	assert.doesNotMatch(r.text, /may appeal/);
});

test('quality complaints remain visible, with no invented sums', () => {
	const r = reviewGuidance(product({
		analyzed: 94, badges: [
			{ category: 'quality', label: 'Poor quality', mentions: 11 },
			{ category: 'not_as_described', label: 'Not as advertised', mentions: 8 }
		]
	}));
	assert.match(r.text, /94 analyzed customer reviews/);
	assert.match(r.text, /11 reviews reported poor quality/);
	assert.doesNotMatch(r.text, /19 reviews/);
});

test('unsupported product qualities and delivery praise do not become suitability claims', () => {
	const r = reviewGuidance(product({
		rows: [
			aspect('Fast delivery', 50, 'positive', 'service'),
			aspect('Comfort', 1),
			aspect('Build quality', 3, 'negative')
		]
	}));
	assert.match(r.text, /not enough specific positive-quality evidence/);
	assert.doesNotMatch(r.text, /may appeal|fast delivery/i);
});

test('no analysis cannot support a recommendation', () => {
	assert.match(reviewGuidance(null).text, /Not enough analyzed/);
	assert.match(reviewGuidance(product({ analyzed: 0 })).text, /Not enough analyzed/);
	assert.match(reviewGuidance(product({ available: false })).text, /Not enough analyzed/);
});

test('poor sentiment never creates a favourable shopping inference', () => {
	const r = reviewGuidance(product({ positive: 12, negative: 70, uncertain: 11 }));
	assert.doesNotMatch(r.text, /may appeal/);
	assert.match(r.text, /does not establish product quality or suitability/);
});

test('a reported high-risk tone overrides missing safety badge', () => {
	const r = reviewGuidance(product({ tone: 'high', badges: [] }));
	assert.equal(r.safety, true);
	assert.match(r.text, /serious safety warning/);
	assert.doesNotMatch(r.text, /may appeal/);
});
