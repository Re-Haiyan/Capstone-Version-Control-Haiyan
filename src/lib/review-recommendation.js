/**
 * Short, non-binding purchase guidance drawn from the existing checker verdict
 * and review sentiment. This changes presentation only: never modify a model
 * decision, warning count, threshold, or stored data.
 *
 * Safety warnings always outrank sentiment. A missing, stale, or unreliable
 * report never gets a positive recommendation, even with a high star rating.
 *
 * @typedef {'consider' | 'caution' | 'alternatives' | 'insufficient'} GuidanceKind
 * @typedef {{kind: GuidanceKind, headline: string}} ReviewRecommendation
 */

/** @param {unknown} value */
const nonnegative = (value) => {
	const count = Number(value);
	return Number.isFinite(count) && count > 0 ? count : 0;
};

/**
 * Return sentiment shares from the weighted marketplace distribution when
 * valid; otherwise use analyzed review counts. Listing stars are not evidence
 * of a sentiment majority.
 *
 * @param {import('./types.js').Product} product
 * @returns {{positive:number, negative:number} | null}
 */
function sentimentShares(product) {
	const summary = product.sentiment_summary;
	const counts = summary?.sentiment_counts;
	const countPositive = nonnegative(counts?.positive);
	const countNegative = nonnegative(counts?.negative);
	const countNeutral = nonnegative(counts?.uncertain ?? counts?.neutral);
	const total = countPositive + countNegative + countNeutral;
	if (total === 0) return null;

	const shares = summary?.sentiment_shares;
	if (shares) {
		const positive = Number(shares.positive);
		const negative = Number(shares.negative);
		const neutral = Number(shares.uncertain ?? shares.neutral);
		if (
			[positive, negative, neutral].every((n) => Number.isFinite(n) && n >= 0 && n <= 1) &&
			Math.abs(positive + negative + neutral - 1) <= 0.02
		) return { positive, negative };
	}
	return { positive: countPositive / total, negative: countNegative / total };
}

/**
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {ReviewRecommendation}
 */
export function reviewRecommendation(product) {
	const view = product?.badge_view;
	const counts = view?.counts ?? {};
	const safetyCount = Math.max(
		nonnegative(counts.safety),
		...(view?.badges ?? [])
			.filter((badge) => badge.category === 'safety')
			.map((badge) => nonnegative(badge.mentions))
	);
	const hasSafety = safetyCount > 0 || view?.tone === 'high' ||
		['safety_warning', 'possible_safety_issue'].includes(view?.state ?? '');

	if (!view?.available || nonnegative(view.reviews_analyzed) === 0 || view.state === 'not_analyzed') {
		return {
			kind: 'insufficient',
			headline: 'There is not enough analyzed review evidence to recommend or advise against this product.'
		};
	}

	// Saved reports keep their historical checker outputs. Do not present an
	// old, potentially outdated report as a current purchase recommendation.
	if (product?.checked_with_current === false) {
		return {
			kind: 'insufficient',
			headline: hasSafety
				? 'This older report includes possible safety concerns. Check the product again before deciding.'
				: 'This report uses an earlier checker. Check the product again for updated purchase guidance.'
		};
	}

	if (view.state === 'insufficient_evidence' || view.state === 'reviews_may_be_unreliable' || view.tone === 'unknown') {
		return {
			kind: 'insufficient',
			headline: hasSafety
				? 'There is not enough reliable review evidence for a recommendation, and a possible safety concern was reported.'
				: 'There is not enough reliable review evidence to recommend or advise against this product.'
		};
	}

	if (view.tone === 'high') {
		return {
			kind: 'alternatives',
			headline: 'Based on the analyzed reviews, we recommend considering alternative products due to reported safety concerns.'
		};
	}

	if (view.tone === 'moderate' || hasSafety) {
		return {
			kind: 'caution',
			headline: hasSafety
				? 'Based on the analyzed reviews, we recommend caution before buying because possible safety concerns were reported.'
				: 'Based on the analyzed reviews, we recommend caution before buying because reviewers reported product concerns.'
		};
	}

	// Only the checker's clear state can yield a positive recommendation.
	// A positive sentiment majority is necessary, but does not prove safety.
	if (view.tone === 'low' && view.state === 'no_warning_signs') {
		const sentiment = sentimentShares(product);
		if (!sentiment) {
			return {
				kind: 'insufficient',
				headline: 'No warning-level issues were detected, but there is not enough sentiment evidence for a purchase recommendation.'
			};
		}
		if (sentiment.positive > 0.5 && sentiment.positive > sentiment.negative) {
			return {
				kind: 'consider',
				headline: 'Based on the analyzed reviews, we recommend considering this product. Most feedback is positive, with no warning-level issues detected.'
			};
		}
		return {
			kind: 'caution',
			headline: sentiment.negative > sentiment.positive
				? 'Based on the analyzed reviews, we recommend comparing alternatives because negative feedback is more common.'
				: 'Based on the analyzed reviews, we recommend reading more feedback before buying because opinions are mixed or unclear.'
		};
	}

	return {
		kind: 'insufficient',
		headline: 'The available review evidence does not support a purchase recommendation.'
	};
}
