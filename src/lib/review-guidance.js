/**
 * Plain-language review summary, shared by every marketplace product category.
 * Never guess the product's purpose or audience: only mention specific traits
 * supported by existing distinct-review aspect evidence.
 *
 * This is descriptive buyer context, NOT a safety claim or a recommendation.
 */
import { positiveHighlights } from './positive-highlights.js';

/** @param {number} count */
const reviewCount = (count) => count === 1 ? '1 review' : count + ' reviews';

/** @param {string[]} items */
function joinNaturally(items) {
	if (!items.length) return '';
	if (items.length === 1) return items[0];
	if (items.length === 2) return items.join(' and ');
	return items.slice(0, -1).join(', ') + ', and ' + items[items.length - 1];
}

/**
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {{ text: string, support: number, analyzed: number, safety: boolean }}
 */
export function reviewGuidance(product) {
	const report = product?.badge_view;
	const analyzed = Math.max(0, Number(report?.reviews_analyzed) || 0);
	const fallback = {
		text: 'There are not enough reviews yet to say what people liked or disliked about this product.',
		support: 0,
		analyzed,
		safety: false
	};
	if (!report?.available || analyzed < 1) return fallback;

	// Real, positive product-specific aspect mentions only; never delivery,
	// seller praise, guesses from listing title, or generic AI claims.
	const qualities = positiveHighlights(report.conclusion, 3).product
		.filter((item) => Number.isInteger(item.reviews) && item.reviews >= 2);
	const praise = qualities.length
		? 'Some reviews praised ' + joinNaturally(
			qualities.map((item) => item.label.toLowerCase() + ' (' + reviewCount(item.reviews) + ')')
		) + '.'
		: "The reviews don't clearly point to specific product qualities that people liked.";

	const badges = (report.badges ?? []).filter((item) => Number(item.mentions) > 0);
	const safetyReports = Math.max(
		0, Number(report.counts?.safety) || 0,
		...badges.filter((item) => item.category === 'safety')
			.map((item) => Number(item.mentions) || 0)
	);
	const safetyWarning = safetyReports > 0 || report.tone === 'high';
	const topProblem = badges
		.filter((item) => item.category !== 'safety')
		.sort((a, b) => Number(b.mentions) - Number(a.mentions))[0];
	const lead = 'We looked at ' + reviewCount(analyzed) + '. ';

	if (safetyWarning) {
		const warning = safetyReports
			? reviewCount(safetyReports) + (safetyReports === 1 ? ' mentions' : ' mention') + ' a possible safety problem.'
			: 'The review checker found a possible serious safety problem.';
		return {
			text: lead + praise + ' However, ' + warning +
				' Please read those reports carefully before deciding whether to buy.',
			support: qualities.length, analyzed, safety: true
		};
	}

	const sentiment = product?.sentiment_summary?.sentiment_counts;
	const positive = Math.max(0, Number(sentiment?.positive) || 0);
	const negative = Math.max(0, Number(sentiment?.negative) || 0);
	const positiveLean = positive > negative && positive > 0;
	const appeal = qualities.length && positiveLean
		? ' If these qualities matter to you, the product may be worth a closer look.'
		: '';
	const concern = topProblem
		? ' However, ' + reviewCount(Number(topProblem.mentions)) +
			' mentioned ' + String(topProblem.label || 'a problem').toLowerCase() +
			'. Read those reviews too.'
		: report.tone === 'moderate'
			? ' The checker also found some concerns worth reading before buying.'
			: ' Reviews alone cannot confirm the product is safe or good quality.';

	return {
		text: lead + praise + appeal + concern,
		support: qualities.length, analyzed, safety: false
	};
}
