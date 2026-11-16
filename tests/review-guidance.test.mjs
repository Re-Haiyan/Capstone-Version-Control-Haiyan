import assert from 'node:assert/strict';
import { test } from 'node:test';
import { reviewGuidance } from '../src/lib/review-guidance.js';

const aspect = (aspect, reviews, polarity = 'positive', kind = 'product') => ({
	kind, aspect, polarity, reviews,
	text: aspect + ': ' + reviews + ' reviews supporting',
	quotes: [{ text: 'A synthetic review about ' + aspect }]
});

const example = ({
	name = 'Synthetic item',
	category = 'other',
	state = 'no_warning_signs',
	analyzed = 93,
	tone = 'low',
	available = true,
	rows = [
		aspect('Value for money', 6),
		aspect('Fit and sizing', 3),
		aspect('Comfort', 2),
		aspect('Delivery', 9, 'positive', 'service')
	],
	badges = [],
	counts = {},
} = {}) => ({
	name, product_category: category,
	badge_view: {
		available, reviews_analyzed: analyzed, state, tone, badges, counts,
		conclusion: { evidence: { reviews_considered: analyzed, why: rows } }
	}
});

const issue = (category, mentions) => ({ category, label: category, mentions });

test('one concise human-readable narrative; grounded positive qualities only', () => {
	const result = reviewGuidance(example());
	assert.equal(result.analyzed, 93);
	assert.equal(result.safety, false);
	assert.equal(result.intro, 'We analyzed 93 reviews.');
	assert.match(result.praise, /value for money \(6 reviews\)/);
	assert.match(result.praise, /fit and sizing \(3 reviews\)/);
	assert.match(result.praise, /comfort \(2 reviews\)/);
	assert.doesNotMatch(result.text, /delivery|safe to buy|guaranteed|synthetic item/i);
	assert.match(result.assessment, /No major warning was triggered/);
	assert.match(result.note, /One review may mention more than one issue/);
	assert.doesNotMatch(result.text, /according to.*model|sentiment classification|warning threshold/i);
});

test('119-review power station: list all concerns once, with safety first in the assessment', () => {
	const result = reviewGuidance(example({
		analyzed: 119, tone: 'low', state: 'no_warning_signs',
		rows: [aspect('Ease of use', 11), aspect('Durability', 8), aspect('Build quality', 4)],
		badges: [
			issue('safety', 1), issue('defect', 14), issue('quality', 2),
			issue('not_as_described', 12)
		]
	}));
	assert.equal(result.intro, 'We analyzed 119 reviews.');
	assert.match(result.praise, /ease of use \(11 reviews\)/);
	assert.match(result.concerns, /14 reviews mentioned faults or failures/);
	assert.match(result.concerns, /12 reviews mentioned differences from the listing/);
	assert.match(result.concerns, /2 reviews mentioned quality concerns/);
	assert.match(result.concerns, /1 review also mentioned a possible safety concern/);
	assert.equal(result.safety, true);
	assert.match(result.assessment, /possible safety concern deserves careful attention/i);
	assert.doesNotMatch(result.assessment, /No major warning was triggered|safe to buy|may be worth/i);
});

test('280-review rice cooker with a safety warning keeps danger in a single assessment', () => {
	const result = reviewGuidance(example({
		analyzed: 280, tone: 'high', state: 'safety_warning',
		rows: [aspect('Value for money', 7)],
		badges: [issue('safety', 6), issue('defect', 29)]
	}));
	assert.equal(result.safety, true);
	assert.match(result.text, /280 reviews/);
	assert.match(result.praise, /value for money \(7 reviews\)/);
	assert.match(result.concerns, /29 reviews mentioned faults or failures/);
	assert.match(result.concerns, /6 reviews also mentioned a possible safety concern/);
	assert.match(result.assessment, /Read the flagged reviews before deciding/);
});

test('positive praise does not override safety even when the backend state is clear', () => {
	const result = reviewGuidance(example({
		state: 'no_warning_signs', tone: 'low', counts: { safety: 1 }
	}));
	assert.equal(result.safety, true);
	assert.match(result.assessment, /possible safety concern/);
	assert.doesNotMatch(result.assessment, /No major warning was triggered/);
});

test('backend badge and counts are overlapping evidence, not added together', () => {
	const result = reviewGuidance(example({
		analyzed: 94, counts: { safety: 1, defect: 14, quality: 2 },
		badges: [issue('safety', 1), issue('defect', 14), issue('not_as_described', 12)]
	}));
	assert.match(result.concerns, /14 reviews mentioned faults or failures/);
	assert.match(result.concerns, /12 reviews mentioned differences from the listing/);
	assert.match(result.concerns, /2 reviews mentioned quality concerns/);
	assert.doesNotMatch(result.concerns, /28 reviews|2 reviews also mentioned a possible safety/);
});

test('authenticity and below-warning defect reports are described without proven counterfeit claims', () => {
	const result = reviewGuidance(example({
		tone: 'moderate', state: 'possible_counterfeit_or_defect',
		badges: [issue('counterfeit', 3), issue('defect', 2)]
	}));
	assert.equal(result.safety, false);
	assert.match(result.concerns, /3 reviews mentioned possible authenticity problems/);
	assert.match(result.concerns, /2 reviews mentioned faults or failures/);
	assert.match(result.assessment, /reported problems deserve closer attention/);
	assert.doesNotMatch(result.text, /is counterfeit|definitely fake/i);
});

test('review reliability warning gets its own assessment even without issue badges', () => {
	const result = reviewGuidance(example({
		tone: 'moderate', state: 'reviews_may_be_unreliable'
	}));
	assert.match(result.assessment, /Some reviews may be unreliable/);
	assert.doesNotMatch(result.assessment, /safe|guaranteed|worth buying/i);
});

test('insufficient information does not sound like a recommendation', () => {
	const result = reviewGuidance(example({
		analyzed: 3, tone: 'unknown', state: 'insufficient_evidence',
		rows: [], counts: { safety: 0 }
	}));
	assert.match(result.intro, /We analyzed 3 reviews/);
	assert.match(result.assessment, /not enough review evidence/i);
	assert.doesNotMatch(result.assessment, /No major warning|buy it|safe to buy/i);
});

test('no report, zero reviewed count or missing breakdown does not invent favorable evidence', () => {
	for (const input of [null, example({ available: false }), example({ analyzed: 0 })]) {
		const result = reviewGuidance(input);
		assert.equal(result.support, 0);
		assert.match(result.text, /not enough analyzed reviews/i);
		assert.doesNotMatch(result.text, /praised|reliable|safe to buy/i);
	}
	const oldReport = reviewGuidance(example({ rows: [], badges: [], counts: {} }));
	assert.match(oldReport.concerns, /does not include a detailed breakdown/);
	assert.doesNotMatch(oldReport.concerns, /No specific issue categories were flagged/);
});

test('delivery praise or uncorroborated positive adjectives never become claims about the product', () => {
	const result = reviewGuidance(example({
		rows: [
			aspect('Fast delivery', 50, 'positive', 'service'),
			aspect('Comfort', 1),
			aspect('Build quality', 3, 'negative')
		]
	}));
	assert.match(result.praise, /do not clearly identify specific product qualities/i);
	assert.doesNotMatch(result.praise, /Fast delivery|Comfort|Build quality/);
});

test('the same evidence creates the same wording in every product category', () => {
	const props = {
		analyzed: 93,
		rows: [aspect('Durability', 7), aspect('Value for money', 4)]
	};
	const products = [
		{ category: 'battery_solar', name: 'Off-grid solar inverter' },
		{ category: 'haircare', name: 'Shampoo' },
		{ category: 'fashion', name: 'Running shoes' },
		{ category: 'food_grocery', name: 'Coffee beans' },
		{ category: 'gaming', name: 'Controller' },
	];
	const baseline = reviewGuidance(example({ ...props, ...products[0] })).text;
	for (const product of products) {
		assert.equal(reviewGuidance(example({ ...props, ...product })).text, baseline);
	}
	assert.doesNotMatch(baseline, /skin|battery|clothing|power output|hair|size|gaming/i);
});
