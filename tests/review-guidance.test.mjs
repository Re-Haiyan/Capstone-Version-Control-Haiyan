import assert from 'node:assert/strict';
import { test } from 'node:test';
import { reviewGuidance } from '../src/lib/review-guidance.js';

const aspect = (aspect, reviews, polarity = 'positive', kind = 'product') => ({
	kind, aspect, polarity, reviews,
	text: aspect + ': ' + reviews + ' reviews supporting',
	quotes: [{ text: 'A fictional review praising ' + aspect }]
});
const product = ({
	name = 'A fictional marketplace item',
	category = 'other',
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
	name, product_category: category,
	sentiment_summary: { sentiment_counts: { positive, negative, uncertain } },
	badge_view: {
		available, reviews_analyzed: analyzed, tone, badges, counts,
		conclusion: { evidence: { reviews_considered: analyzed, why: rows } }
	}
});

test('quick summary reads naturally and uses real counts, never listing text', () => {
	const result = reviewGuidance(product());
	assert.equal(result.analyzed, 93);
	assert.equal(result.safety, false);
	assert.match(result.text, /^We looked at 93 reviews\./);
	assert.match(result.text, /value for money \(6 reviews\)/);
	assert.match(result.text, /fit and sizing \(3 reviews\)/);
	assert.match(result.text, /comfort \(2 reviews\)/);
	assert.match(result.text, /If these qualities matter to you/);
	assert.doesNotMatch(result.text, /delivery|safe to buy|guaranteed|fictional marketplace/i);
});

test('safety findings are stated plainly before any buyer suggestion', () => {
	const r = reviewGuidance(product({
		analyzed: 355, tone: 'moderate',
		positive: 138, negative: 178, uncertain: 39,
		badges: [{ category: 'safety', label: 'Safety problem', mentions: 3 }]
	}));
	assert.equal(r.safety, true);
	assert.match(r.text, /We looked at 355 reviews/);
	assert.match(r.text, /3 reviews mention a possible safety problem/);
	assert.doesNotMatch(r.text, /may be worth a closer look|safe to buy|recommend buying/i);
});

test('even one safety report overrides positive comments', () => {
	const r = reviewGuidance(product({ counts: { safety: 1 } }));
	assert.equal(r.safety, true);
	assert.match(r.text, /1 review mentions a possible safety problem/);
	assert.doesNotMatch(r.text, /may be worth a closer look/);
});

test('other complaints are never hidden or added together', () => {
	const r = reviewGuidance(product({
		analyzed: 94, badges: [
			{ category: 'quality', label: 'Poor quality', mentions: 11 },
			{ category: 'not_as_described', label: 'Not as advertised', mentions: 8 }
		]
	}));
	assert.match(r.text, /We looked at 94 reviews/);
	assert.match(r.text, /11 reviews mentioned poor quality/);
	assert.doesNotMatch(r.text, /19 reviews/);
});

test('no general purchase claim from delivery praise, one-offs, or negative traits', () => {
	const r = reviewGuidance(product({
		rows: [
			aspect('Fast delivery', 50, 'positive', 'service'),
			aspect('Comfort', 1),
			aspect('Build quality', 3, 'negative')
		]
	}));
	assert.match(r.text, /don't clearly point to specific product qualities/);
	assert.doesNotMatch(r.text, /may be worth a closer look|fast delivery/i);
});

test('missing or unavailable results cannot support a favourable statement', () => {
	assert.match(reviewGuidance(null).text, /not enough reviews yet/i);
	assert.match(reviewGuidance(product({ analyzed: 0 })).text, /not enough reviews yet/i);
	assert.match(reviewGuidance(product({ available: false })).text, /not enough reviews yet/i);
});

test('negative overall feedback never triggers a buyer-suitability statement', () => {
	const r = reviewGuidance(product({ positive: 12, negative: 70, uncertain: 11 }));
	assert.doesNotMatch(r.text, /may be worth a closer look/);
	assert.match(r.text, /Reviews alone cannot confirm/);
});

test('a high risk status takes priority even if the safety detail is absent', () => {
	const r = reviewGuidance(product({ tone: 'high', badges: [] }));
	assert.equal(r.safety, true);
	assert.match(r.text, /possible serious safety problem/);
	assert.doesNotMatch(r.text, /may be worth a closer look/);
});

test('same evidence yields same copy for any product category (no assumptions)', () => {
	const props = {
		analyzed: 93,
		rows: [aspect('Durability', 7), aspect('Value for money', 4)]
	};
	const devices = [
		{ category: 'battery_solar', name: 'Off-grid solar inverter' },
		{ category: 'haircare', name: 'Shampoo' },
		{ category: 'fashion', name: 'Running shoes' },
		{ category: 'food_grocery', name: 'Coffee beans' },
		{ category: 'gaming', name: 'Controller' },
	];
	const text = reviewGuidance(product({ ...props, ...devices[0] })).text;
	for (const device of devices) {
		assert.equal(reviewGuidance(product({ ...props, ...device })).text, text);
	}
	assert.doesNotMatch(text, /skin|battery|clothing|power output|hair|size|gaming/i);
});
