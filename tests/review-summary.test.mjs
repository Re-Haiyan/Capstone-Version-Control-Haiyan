import assert from 'node:assert/strict';
import { test } from 'node:test';
import { reviewSummary } from '../src/lib/review-summary.js';

const report = ({
	available = true, analyzed = 94, tone = 'low',
	positive = 80, negative = 8, uncertain = 6, badges = [], counts = {}
} = {}) => ({
	sentiment_summary: {
		sentiment_counts: { positive, negative, uncertain }
	},
	badge_view: {
		available, reviews_analyzed: analyzed, tone, badges, counts
	}
});

test('positive feedback gets a measured non-guarantee summary', () => {
	const out = reviewSummary(report());
	assert.equal(out.kind, 'balanced');
	assert.match(out.text, /94 sentiment-labelled reviews/);
	assert.match(out.text, /most feedback is positive/);
	assert.match(out.text, /No warning-level issues were flagged in this sample/);
	assert.doesNotMatch(out.text, /safe to buy|guaranteed safe|recommended to buy/i);
});

test('a single reported safety concern always overrides a positive majority', () => {
	const out = reviewSummary(report({
		badges: [{ category: 'safety', label: 'Safety problem', mentions: 1 }]
	}));
	assert.equal(out.kind, 'safety');
	assert.match(out.text, /1 review mention possible safety concerns/);
	assert.match(out.text, /Read the flagged reviews carefully/);
	assert.doesNotMatch(out.text, /safe to buy/i);
});

test('safety count from legacy risk summary also wins', () => {
	const out = reviewSummary(report({
		tone: 'low', badges: [], counts: { safety: 3 }
	}));
	assert.equal(out.kind, 'safety');
	assert.match(out.text, /3 reviews mention/);
});

test('below-warning complaints cannot be summarized as unqualified praise', () => {
	const out = reviewSummary(report({
		badges: [{ category: 'quality', label: 'Poor quality', mentions: 11 }]
	}));
	assert.equal(out.kind, 'caution');
	assert.match(out.text, /poor quality \(11 reviews\)/);
	assert.match(out.text, /did not reach the warning threshold/);
});

test('moderate verdict reports the issue counts without summing categories', () => {
	const out = reviewSummary(report({
		tone: 'moderate',
		badges: [
			{ category: 'defect', label: 'Faulty or broken', mentions: 2 },
			{ category: 'quality', label: 'Poor quality', mentions: 11 },
			{ category: 'not_as_described', label: 'Not as advertised', mentions: 8 }
		]
	}));
	assert.equal(out.kind, 'caution');
	assert.match(out.text, /poor quality in 11 reviews/);
	assert.doesNotMatch(out.text, /21 reviews/);
});

test('a high-severity verdict is not downgraded when badge details are omitted', () => {
	const out = reviewSummary(report({ tone: 'high' }));
	assert.equal(out.kind, 'safety');
	assert.match(out.text, /flags a potential safety concern/);
});

test('insufficient data produces no recommendation or reassuring claim', () => {
	const none = reviewSummary(null);
	assert.equal(none.kind, 'unknown');
	assert.match(none.text, /Not enough analyzed/);
	const unavailable = reviewSummary(report({ available: false }));
	assert.equal(unavailable.kind, 'unknown');
});

test('sentiment wording uses labelled support rather than claiming unlabelled reviews agreed', () => {
	const out = reviewSummary(report({ analyzed: 94, positive: 7, negative: 2, uncertain: 1 }));
	assert.match(out.text, /10 sentiment-labelled reviews/);
	assert.doesNotMatch(out.text, /94 sentiment-labelled reviews/);
});

test('absence of sentiment counts is not treated as positive feedback', () => {
	const out = reviewSummary(report({ positive: 0, negative: 0, uncertain: 0 }));
	assert.match(out.text, /do not provide a clear sentiment breakdown/);
	assert.doesNotMatch(out.text, /most feedback is positive/);
});
