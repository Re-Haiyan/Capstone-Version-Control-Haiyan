/**
 * Short review-based suitability context for the classic DeFaketive report.
 *
 * Grounds *all* highlighted qualities in distinct, quoted review-aspect
 * evidence, and always prioritizes risk flags. This is never proof of product
 * safety, real-world suitability, authenticity, or a recommendation to buy.
 *
 * The archived report's saved model results are never changed here.
 */

import { positiveHighlights } from './positive-highlights.js';

/** @param {number} value */
const reviews = (value) => value === 1 ? '1 review' : value + ' reviews';

/** @param {string[]} labels */
function list(labels) {
	if (labels.length === 0) return '';
	if (labels.length === 1) return labels[0];
	if (labels.length === 2) return labels.join(' and ');
	return labels.slice(0, -1).join(', ') + ', and ' + labels[labels.length - 1];
}

/**
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {{ text: string, support: number, analyzed: number, safety: boolean }}
 */
export function reviewGuidance(product) {
	const view = product?.badge_view;
	const analyzed = Math.max(0, Number(view?.reviews_analyzed) || 0);
	const fallback = {
		text: 'Not enough analyzed review evidence is available to describe who this product may suit.',
		support: 0,
		analyzed,
		safety: false
	};
	if (!view?.available || analyzed < 1) return fallback;

	const highlights = positiveHighlights(view.conclusion, 3).product;
	const supported = highlights.filter((item) => Number(item.reviews) >= 2);
	const qualities = supported.map((item) => item.label.toLowerCase());
	const badges = (view.badges ?? []).filter((item) => Number(item.mentions) > 0);
	const safety = Math.max(
		0,
		Number(view.counts?.safety) || 0,
		...badges.filter((item) => item.category === 'safety').map((item) => Number(item.mentions) || 0)
	);
	const highRisk = safety > 0 || view.tone === 'high';
	const otherIssues = badges
		.filter((item) => item.category !== 'safety')
		.sort((a, b) => Number(b.mentions) - Number(a.mentions));
	const topIssue = otherIssues[0];
	const countLabel = 'According to ' + analyzed + ' analyzed customer ' + (analyzed === 1 ? 'review, ' : 'reviews, ');
	const q = supported.map((item) => item.label.toLowerCase() + ' (' + reviews(item.reviews) + ')');
	const praise = supported.length
		? 'some reviewers praised ' + list(q) + '.'
		: 'there is not enough specific positive-quality evidence to identify a clear buyer preference.';

	if (highRisk) {
		return {
			text: countLabel + praise + ' However, ' + (safety > 0
				? reviews(safety) + (safety === 1 ? ' mentions' : ' mention') + ' a possible safety concern.'
				: 'the checker raised a serious safety warning.') +
				' Review these reports carefully; this product cannot be considered safe based on customer reviews alone.',
			support: supported.length,
			analyzed,
			safety: true
		};
	}

	const sentiment = product?.sentiment_summary?.sentiment_counts;
	const positive = Number(sentiment?.positive) || 0;
	const negative = Number(sentiment?.negative) || 0;
	const hasPositiveLean = positive > negative && positive > 0;

	const appeal = supported.length && hasPositiveLean
		? ' It may appeal to shoppers who prioritize ' + list(qualities) + '.'
		: '';
	const concern = topIssue
		? ' However, ' + reviews(Number(topIssue.mentions)) + ' reported ' +
			String(topIssue.label || 'a problem').toLowerCase() + '; check those reviews before deciding.'
		: view.tone === 'moderate'
			? ' The checker also found concerns worth reviewing before any purchase.'
			: ' This does not establish product quality or suitability.';

	return {
		text: countLabel + praise + appeal + concern,
		support: supported.length,
		analyzed,
		safety: false
	};
}
