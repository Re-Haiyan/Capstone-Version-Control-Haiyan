/**
 * Small, informational product-category label for the Review Summary card.
 * Use only the product_category persisted by the backend, never guess from the
 * browser-side title or a review. This must not influence sentiment or flags.
 *
 * @param {import('./types.js').Product | null | undefined} product
 * @returns {{label: string, stale: boolean, explanation: string}}
 */
export function categoryForReport(product) {
	const slug = typeof product?.product_category === 'string'
		? product.product_category.trim().toLowerCase()
		: '';
	const stale = product?.checked_with_current === false;

	// Old reports with no category are not retrospectively classified in the UI.
	if (!slug) {
		return {
			label: 'Not recorded',
			stale,
			explanation: 'This report has no saved product category. Check the product again to identify it.'
		};
	}
	if (slug === 'other') {
		return {
			label: 'Unclassified',
			stale,
			explanation: stale
				? 'This older report could not identify a category. Check again with the latest rules.'
				: 'The product title did not match a specific category.'
		};
	}

	// Product categories are backend-generated snake_case taxonomy values.
	// Do not show arbitrary malformed data in a trusted-looking category pill.
	if (!/^[a-z][a-z0-9_]{0,49}$/.test(slug)) {
		return {
			label: 'Unclassified',
			stale,
			explanation: 'This report contains an invalid category value.'
		};
	}

	const special = {
		battery_solar: 'Battery & Solar',
		tv_display: 'TV & Display',
		home_decor_lighting: 'Home Decor & Lighting',
		crafts_diy: 'Crafts & DIY'
	};
	const label = Object.hasOwn(special, slug)
		? /** @type {Record<string, string>} */ (special)[slug]
		: slug.split('_').filter(Boolean).map(word => word[0].toUpperCase() + word.slice(1)).join(' ');

	return {
		label,
		stale,
		explanation: stale
			? 'Saved category from an earlier checker version. Recheck the product to update it.'
			: 'Automatically identified from the product listing title. This is an estimate, not a verified classification.'
	};
}
