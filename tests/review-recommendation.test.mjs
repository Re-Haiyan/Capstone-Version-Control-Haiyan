import assert from 'node:assert/strict';
import { test } from 'node:test';
import { reviewRecommendation } from '../src/lib/review-recommendation.js';

function report({
	state = 'no_warning_signs',
	tone = 'low',
	safety = 0,
	positive = 80,
	negative = 10,
	uncertain = 10,
	shares,
	available = true,
	analyzed = 100,
	checked_with_current = true
} = {}) {
	return {
		checked_with_current,
		rating: 4.9,
		badge_view: {
			available,
			state,
			tone,
			reviews_analyzed: analyzed,
			counts: { safety },
			badges: []
		},
		sentiment_summary: {
			sentiment_counts: { positive, negative, uncertain },
			...(shares === undefined ? {} : { sentiment_shares: shares })
		}
	};
}

test('recommend considering only for a positive majority and clear checker verdict', () => {
	const rec = reviewRecommendation(report());
	assert.equal(rec.kind, 'consider');
	assert.match(rec.headline, /we recommend considering this product/i);
	assert.match(rec.headline, /no warning-level concerns/i);
});

test('a serious safety warning overrides even 99 percent positive sentiment', () => {
	const rec = reviewRecommendation(report({
		state: 'safety_warning', tone: 'high', safety: 3,
		shares: { positive: 0.99, negative: 0.01, uncertain: 0 }
	}));
	assert.equal(rec.kind, 'alternatives');
	assert.match(rec.headline, /considering alternative products/i);
	assert.match(rec.headline, /reported possible safety concerns/i);
});

test('one safety mention lifts an otherwise low-risk product to caution', () => {
	const rec = reviewRecommendation(report({ safety: 1 }));
	assert.equal(rec.kind, 'caution');
	assert.match(rec.headline, /possible safety concerns/i);
});

test('safety mentions in badges are recognized even if counts are absent', () => {
	const input = report();
	input.badge_view.counts = {};
	input.badge_view.badges = [{ category: 'safety', mentions: 1 }];
	assert.equal(reviewRecommendation(input).kind, 'caution');
});

test('a moderate defect or counterfeit risk triggers caution, never a positive recommendation', () => {
	for (const state of ['possible_counterfeit_or_defect', 'possible_safety_issue']) {
		const rec = reviewRecommendation(report({ state, tone: 'moderate' }));
		assert.equal(rec.kind, 'caution');
	}
});

test('weighted sentiment takes precedence over deliberately oversampled low-star review counts', () => {
	const rec = reviewRecommendation(report({
		positive: 20, negative: 70, uncertain: 10,
		shares: { positive: 0.7, negative: 0.2, uncertain: 0.1 }
	}));
	assert.equal(rec.kind, 'consider');
});

test('a clear checker verdict with majority negative sentiment is not recommended', () => {
	const rec = reviewRecommendation(report({
		shares: { positive: 0.2, negative: 0.6, uncertain: 0.2 }
	}));
	assert.equal(rec.kind, 'caution');
	assert.match(rec.headline, /negative feedback is more common/i);
});

test('a clear checker verdict with mixed sentiment calls for further reading', () => {
	const rec = reviewRecommendation(report({
		shares: { positive: 0.4, negative: 0.4, uncertain: 0.2 }
	}));
	assert.equal(rec.kind, 'caution');
	assert.match(rec.headline, /mixed or unclear/i);
});

test('missing sentiment cannot generate a favorable recommendation', () => {
	const rec = reviewRecommendation(report({
		positive: 0, negative: 0, uncertain: 0, shares: undefined
	}));
	assert.equal(rec.kind, 'insufficient');
});

test('unanalysed and insufficient-evidence reports do not recommend purchase', () => {
	const states = [
		report({ available: false }),
		report({ analyzed: 0 }),
		report({ state: 'insufficient_evidence', tone: 'unknown' }),
		report({ state: 'reviews_may_be_unreliable', tone: 'unknown' })
	];
	for (const input of states) assert.equal(reviewRecommendation(input).kind, 'insufficient');
	assert.equal(reviewRecommendation(null).kind, 'insufficient');
});

test('an uncertain report still mentions a possible safety concern', () => {
	const rec = reviewRecommendation(report({ state: 'insufficient_evidence', tone: 'unknown', safety: 1 }));
	assert.equal(rec.kind, 'insufficient');
	assert.match(rec.headline, /possible safety concern/i);
});

test('stale saved reports are never presented as current purchase guidance', () => {
	const rec = reviewRecommendation(report({ checked_with_current: false }));
	assert.equal(rec.kind, 'insufficient');
	assert.match(rec.headline, /earlier checker/i);
	const staleWarning = reviewRecommendation(report({
		tone: 'high', state: 'safety_warning', safety: 2, checked_with_current: false
	}));
	assert.equal(staleWarning.kind, 'insufficient');
	assert.match(staleWarning.headline, /possible safety concerns/i);
});


test('each outcome is expressed as a single natural sentence rather than a label list', () => {
	const cases = [
		report(),
		report({ state: 'safety_warning', tone: 'high', safety: 3 }),
		report({ state: 'possible_safety_issue', tone: 'moderate', safety: 1 }),
		report({ state: 'possible_counterfeit_or_defect', tone: 'moderate' }),
		report({ state: 'insufficient_evidence', tone: 'unknown' }),
		report({ state: 'insufficient_evidence', tone: 'unknown', safety: 1 }),
		report({ state: 'reviews_may_be_unreliable', tone: 'unknown' }),
		report({ checked_with_current: false }),
		report({ checked_with_current: false, state: 'safety_warning', tone: 'high', safety: 1 }),
		report({ available: false }),
		report({ positive: 0, negative: 0, uncertain: 0 }),
		report({ shares: { positive: 0.2, negative: 0.6, uncertain: 0.2 } }),
		report({ shares: { positive: 0.4, negative: 0.4, uncertain: 0.2 } }),
		null
	];
	for (const input of cases) {
		const { headline } = reviewRecommendation(input);
		assert.equal((headline.match(/[.!?](?=\\s|$)/g) ?? []).length, 1, headline);
		assert.ok(headline.length <= 230, 'Summary should remain compact');
	}
});
