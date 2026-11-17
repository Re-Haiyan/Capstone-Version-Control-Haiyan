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
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {{positive:number, negative:number} | null}
 */
function sentimentShares(product) {
	const summary = product?.sentiment_summary;
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
			headline: 'Based on the available information, we cannot recommend or advise against this product because too few analyzed reviews are available.'
		};
	}

	// Saved reports keep their historical checker outputs. Do not present an
	// old, potentially outdated report as a current purchase recommendation.
	if (product?.checked_with_current === false) {
		return {
			kind: 'insufficient',
			headline: hasSafety
				? 'Because this older report includes possible safety concerns, we recommend checking the product again before deciding whether to buy.'
				: 'Because this report used an earlier checker, we recommend checking the product again for updated purchase guidance.'
		};
	}

	if (view.state === 'insufficient_evidence' || view.state === 'reviews_may_be_unreliable' || view.tone === 'unknown') {
		return {
			kind: 'insufficient',
			headline: hasSafety
				? 'Based on the available reviews, we cannot make a reliable purchase recommendation because the evidence is limited and a possible safety concern was reported.'
				: 'Based on the available reviews, we cannot recommend or advise against this product because the evidence is insufficient or unreliable.'
		};
	}

	if (view.tone === 'high') {
		return {
			kind: 'alternatives',
			headline: 'Based on the analyzed reviews, we recommend considering other products because some reviewers reported possible safety concerns.'
		};
	}

	if (view.tone === 'moderate' || hasSafety) {
		return {
			kind: 'caution',
			headline: hasSafety
				? 'Based on the analyzed reviews, we recommend buying with caution because some reviewers mentioned possible safety concerns.'
				: 'Based on the analyzed reviews, we recommend buying with caution because some reviewers reported problems with the product.'
		};
	}

	// Only the checker's clear state can yield a positive recommendation.
	// A positive sentiment majority is necessary, but does not prove safety.
	if (view.tone === 'low' && view.state === 'no_warning_signs') {
		const sentiment = sentimentShares(product);
		if (!sentiment) {
			return {
				kind: 'insufficient',
				headline: 'Although the checker found no warning-level issues, we cannot recommend buying this product because there is not enough sentiment evidence.'
			};
		}
		if (sentiment.positive > 0.5 && sentiment.positive > sentiment.negative) {
			return {
				kind: 'consider',
				headline: 'Based on the analyzed reviews, we recommend considering this product because most feedback is positive and no warning-level concerns were detected.'
			};
		}
		return {
			kind: 'caution',
			headline: sentiment.negative > sentiment.positive
				? 'Based on the analyzed reviews, we recommend comparing other products because negative feedback is more common than positive feedback.'
				: 'Based on the analyzed reviews, we recommend reviewing more customer feedback before buying because opinions are mixed or unclear.'
		};
	}

	return {
		kind: 'insufficient',
		headline: 'Based on the available reviews, we cannot make a reliable purchase recommendation without stronger evidence.'
	};
}
