/**
 * Single shopper-friendly, evidence-led review narrative for EVERY report
 * status. Counts are distinct reviews per *category* and may overlap.
 *
 * This is strictly display text: no models, thresholds, stored verdicts,
 * category classification or flags are modified here. A listing title and
 * star rating are NOT sufficient evidence for a review-based claim.
 */
import { positiveHighlights } from './positive-highlights.js';

const REVIEWED_ISSUES = Object.freeze([
	['defect', 'faults or failures'],
	['not_as_described', 'differences from the listing'],
	['quality', 'quality concerns'],
	['counterfeit', 'possible authenticity problems'],
]);

/** @param {number} count */
const reviewCount = (count) => count === 1 ? '1 review' : count + ' reviews';

/** @param {string[]} items */
function joinNaturally(items) {
	if (items.length === 0) return '';
	if (items.length === 1) return items[0];
	if (items.length === 2) return items.join(' and ');
	return items.slice(0, -1).join(', ') + ', and ' + items.at(-1);
}

/**
 * @typedef {{
 * text: string,
 * intro: string,
 * praise: string,
 * concerns: string,
 * assessment: string,
 * note: string,
 * support: number,
 * analyzed: number,
 * safety: boolean
 * }} ReviewGuidance
 */

/**
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {ReviewGuidance}
 */
export function reviewGuidance(product) {
	const report = product?.badge_view;
	const analyzed = Math.max(0, Math.floor(Number(report?.reviews_analyzed) || 0));
	const note = 'Based on customer-reported reviews, not independent product testing. One review may mention more than one issue.';

	// A stale or unanalysed product must NOT get a favourable-looking summary
	// merely because there is a rating or a marketplace product title.
	if (!report?.available || analyzed < 1) {
		const text = 'There are not enough analyzed reviews to summarize this product.';
		return {
			text, intro: text, praise: '', concerns: '',
			assessment: 'Check the product and seller details before making a decision.',
			note, support: 0, analyzed, safety: false
		};
	}

	const intro = 'We analyzed ' + reviewCount(analyzed) + '.';
	const qualities = positiveHighlights(report.conclusion, 3).product
		.filter((item) => Number.isInteger(item.reviews) && item.reviews >= 2);
	const praise = qualities.length
		? 'Some reviewers praised ' + joinNaturally(
			qualities.map((item) => item.label.toLowerCase() + ' (' + reviewCount(item.reviews) + ')')
		) + '.'
		: 'The available reviews do not clearly identify specific product qualities people liked.';

	// Only supported category counts. An old report can omit a badge but keep
	// its count, so use the larger count rather than hiding a reported issue.
	/** @type {Map<string, number>} */
	const issueCounts = new Map();
	for (const [category, count] of Object.entries(report.counts ?? {})) {
		const value = Number(count);
		if (Number.isSafeInteger(value) && value > 0) issueCounts.set(category, value);
	}
	for (const item of report.badges ?? []) {
		const value = Number(item.mentions);
		if (Number.isSafeInteger(value) && value > 0) {
			issueCounts.set(item.category, Math.max(issueCounts.get(item.category) || 0, value));
		}
	}

	const safetyReports = issueCounts.get('safety') || 0;
	const hasSafety = safetyReports > 0 || report.state === 'safety_warning' || report.tone === 'high';
	const isInsufficient = report.state === 'insufficient_evidence' || report.state === 'not_analyzed'
		|| report.tone === 'unknown';
	const otherIssues = REVIEWED_ISSUES
		.filter(([category]) => (issueCounts.get(category) || 0) > 0)
		.map(([category, issue]) => ({
			category,
			count: issueCounts.get(category) || 0,
			text: reviewCount(issueCounts.get(category) || 0) + ' mentioned ' + issue,
		}));
	const hasReportedIssues = otherIssues.length > 0 || safetyReports > 0;
	const hasIssueData = (report.badges?.length || 0) > 0
		|| Object.keys(report.counts ?? {}).length > 0;
	const issueSentences = [];
	if (otherIssues.length) {
		issueSentences.push(
			(qualities.length ? 'However, ' : 'In the analyzed reviews, ')
			+ joinNaturally(otherIssues.map((item) => item.text)) + '.'
		);
	}
	if (safetyReports > 0) {
		issueSentences.push(
			reviewCount(safetyReports)
			+ ' also mentioned'
			+ ' a possible safety concern.'
		);
	} else if (hasSafety) {
		issueSentences.push('The checker also raised a possible safety warning.');
	}
	const concerns = issueSentences.length
		? issueSentences.join(' ')
		: !hasIssueData
			? 'This saved report does not include a detailed breakdown of reported issues.'
			: 'No specific issue categories were flagged in this sample.';

	let assessment;
	if (hasSafety) {
		assessment = 'A possible safety concern deserves careful attention, even if other feedback is positive. Read the flagged reviews before deciding whether to buy.';
	} else if (isInsufficient) {
		assessment = 'There is not enough review evidence for a confident assessment. Check product details and seller information before deciding.';
	} else if (report.state === 'reviews_may_be_unreliable') {
		assessment = 'Some reviews may be unreliable. Check the supporting reviews and seller information before making a decision.';
	} else if (report.state === 'possible_counterfeit_or_defect' || report.tone === 'moderate') {
		assessment = 'The reported problems deserve closer attention. Compare the flagged reviews with the listing before deciding whether to buy.';
	} else if (hasReportedIssues) {
		assessment = 'Some reviews still describe problems, even though the checker did not raise a major warning. Read those reviews before deciding whether to buy.';
	} else {
		assessment = 'No major warning was triggered in the available sample. This does not establish that the product is safe or reliable.';
	}

	const text = [intro, praise, concerns, assessment].filter(Boolean).join(' ');
	return {
		text, intro, praise, concerns, assessment, note,
		support: qualities.length, analyzed, safety: hasSafety
	};
}
