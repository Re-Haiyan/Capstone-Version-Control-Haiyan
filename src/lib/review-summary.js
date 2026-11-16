/**
 * A conservative short summary grounded in saved review sentiment counts
 * and the production checker. NEVER assert product safety, invent a buying
 * recommendation, or sum overlapping issue-category counts.
 */

/**
 * @typedef {{ kind: 'safety' | 'caution' | 'balanced' | 'unknown',
 *  text: string, note: string, analyzed: number }} ReviewSummary
 */

/** @param {number} n */
function count(n) {
	return n === 1 ? '1 review' : n + ' reviews';
}

/**
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {ReviewSummary}
 */
export function reviewSummary(product) {
	const view = product?.badge_view;
	const counts = product?.sentiment_summary?.sentiment_counts;
	const analyzed = Math.max(0, Number(view?.reviews_analyzed) || 0);
	const positive = Math.max(0, Number(counts?.positive) || 0);
	const negative = Math.max(0, Number(counts?.negative) || 0);
	const uncertain = Math.max(0, Number(counts?.uncertain ?? counts?.neutral) || 0);
	const tally = positive + negative + uncertain;
	const note = 'This summary describes review patterns only; it is not a purchase recommendation.';

	if (!view?.available || analyzed === 0) {
		return {
			kind: 'unknown',
			text: 'Not enough analyzed review evidence is available to summarize this product.',
			note, analyzed
		};
	}

	const sentiment = tally === 0
		? 'The analyzed reviews do not provide a clear sentiment breakdown.'
		: positive > tally / 2
			? 'According to the ' + tally + ' sentiment-labelled reviews, most feedback is positive.'
			: negative > tally / 2
				? 'According to the ' + tally + ' sentiment-labelled reviews, most feedback is negative.'
				: positive > negative
					? 'According to the ' + tally + ' sentiment-labelled reviews, positive feedback is more common than negative feedback.'
					: negative > positive
						? 'According to the ' + tally + ' sentiment-labelled reviews, negative feedback is more common than positive feedback.'
						: 'The ' + tally + ' sentiment-labelled reviews show mixed or unclear feedback.';

	const badges = (view.badges ?? []).filter((badge) => Number(badge.mentions) > 0);
	const safety = badges.find((badge) => badge.category === 'safety');
	// The risk counts can also signal safety mentions in a legacy saved report.
	const safetyCount = Math.max(
		Number(safety?.mentions) || 0,
		Number(view.counts?.safety) || 0
	);
	const high = view.tone === 'high';
	const moderate = view.tone === 'moderate';

	if (high || safetyCount > 0) {
		return {
			kind: 'safety',
			text: sentiment + ' However, ' + (safetyCount > 0
				? count(safetyCount) + (safetyCount === 1 ? ' mentions' : ' mention') + ' possible safety concerns.'
				: 'the checker flags a potential safety concern.') + ' Read the flagged reviews carefully before deciding.',
			note, analyzed
		};
	}

	// Category counts may overlap. Quote only the top category's own count.
	const topIssue = [...badges].sort((a, b) => Number(b.mentions) - Number(a.mentions))[0];
	if (moderate) {
		return {
			kind: 'caution',
			text: sentiment + (topIssue
				? ' The checker also flagged ' + topIssue.label.toLowerCase() + ' in ' + count(Number(topIssue.mentions)) + '.'
				: ' The checker also found issues that deserve closer attention.') + ' Read those reviews before deciding.',
			note, analyzed
		};
	}
	if (topIssue) {
		return {
			kind: 'caution',
			text: sentiment + ' Some reviews still report ' + topIssue.label.toLowerCase() + ' (' + count(Number(topIssue.mentions)) + '); these did not reach the warning threshold.',
			note, analyzed
		};
	}
	if (view.tone === 'low') {
		return {
			kind: 'balanced',
			text: sentiment + ' No warning-level issues were flagged in this sample.',
			note, analyzed
		};
	}
	return {
		kind: 'unknown',
		text: sentiment + ' The checker does not have enough evidence for a reliable risk assessment.',
		note, analyzed
	};
}
