/** Category discovery returns a results grid, rather than a report for the category URL.
 * @param {string} value
 */
export function isLazadaCategoryUrl(value) {
	try {
		const url = new URL(value);
		return /^https?:$/.test(url.protocol) && ['lazada.com.ph', 'www.lazada.com.ph'].includes(url.hostname) &&
			(url.pathname.startsWith('/shop-') || url.pathname.startsWith('/category/') || url.pathname.replace(/\/$/, '') === '/catalog');
	} catch { return false; }
}
