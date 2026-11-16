/**
 * Positive themes drawn exclusively from existing review-grounded aspect
 * evidence, not new generated claims, star ratings, or marketing text.
 * Backend evidence already counts DISTINCT reviews per feature.
 */

/**
 * @typedef {{key:string,label:string,reviews:number,concerns:number,quotes:string[]}} PositiveHighlight
 */

/**
 * @param {import('./types.js').Conclusion | null | undefined} conclusion
 * @param {number} [limit]
 * @returns {{ product: PositiveHighlight[], service: PositiveHighlight[], reviewed: number, available: boolean }}
 */
export function positiveHighlights(conclusion, limit = 4) {
	const evidence = conclusion?.evidence;
	if (!evidence || !Array.isArray(evidence.why)) {
		return { product: [], service: [], reviewed: 0, available: false };
	}

	const negatives = new Map();
	for (const row of evidence.why) {
		if (row.kind !== 'product' || row.polarity !== 'negative') continue;
		negatives.set(row.aspect, (negatives.get(row.aspect) || 0) + Math.max(0, Number(row.reviews) || 0));
	}

	/** @type {PositiveHighlight[]} */
	const product = [];
	/** @type {PositiveHighlight[]} */
	const service = [];
	for (const row of evidence.why) {
		if (row.polarity !== 'positive' || !['product', 'service'].includes(row.kind)) continue;
		const count = Number(row.reviews);
		if (!Number.isInteger(count) || count < 1) continue;

		// Server supplies e.g. "Comfort: 5 reviews supporting" (grounded).
		const label = String(row.text || '').split(/:\s*/)[0]?.trim().replace(/\s+/g, ' ') || '';
		if (!label || label.length > 65) continue;
		const concernCount = negatives.get(row.aspect) || 0;
		// Don't promote a feature criticised at least as often as praised.
		if (row.kind === 'product' && concernCount >= count) continue;

		const entry = {
			key: row.kind + ':' + row.aspect,
			label,
			reviews: count,
			concerns: concernCount,
			quotes: (row.quotes ?? [])
				.map((q) => String(q.text || '').trim())
				.filter(Boolean)
				.slice(0, 2)
		};
		if (row.kind === 'product') product.push(entry);
		else service.push(entry);
	}

	/** @type {(a: PositiveHighlight, b: PositiveHighlight) => number} */
	const order = (a, b) => b.reviews - a.reviews || a.label.localeCompare(b.label);
	product.sort(order);
	service.sort(order);
	const max = Number.isInteger(limit) ? Math.max(0, Math.min(limit, 6)) : 4;

	return {
		product: product.slice(0, max),
		service: service.slice(0, 1),
		reviewed: Math.max(0, Number(evidence.reviews_considered) || 0),
		available: true
	};
}

/** @param {number} n */
export function reviewMentionCount(n) {
	return n === 1 ? '1 review' : String(n) + ' reviews';
}
