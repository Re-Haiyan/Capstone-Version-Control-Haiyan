/**
 * Lightweight, read-only audit summary for panel flow step 3.
 * Only count backend-supplied category-context metadata from analyzed reviews.
 * Old reports without metadata do not show invented pass/fail results.
 * @param {import('./types.js').Product | undefined | null} product
 */
export function categoryContextSummary(product) {
  const counts = {
    checked: 0, agrees: 0, differs: 0, ambiguous: 0, noSignal: 0,
    unclassified: 0, matched: 0, expectedBehavior: 0, unavailable: 0
  };
  // Unknown/new statuses are not silently counted as "no signal"; older
  // reports or malformed metadata must never invent completed checks.
  const validStatuses = new Set([
    'agrees', 'differs', 'ambiguous', 'no_signal',
    'unclassified', 'unavailable', 'expected_behavior'
  ]);
  for (const review of product?.comments ?? []) {
    if (review?.included_in_analysis === false) continue;
    const data = review?.sentiment_analysis?.sentiment?.category_context;
    if (!data || !['category-context-v1', 'category-context-v2'].includes(data.revision) ||
        data.used_for_decision !== false || data.sentiment_overridden !== false ||
        !validStatuses.has(data.status)) continue;
    counts.checked++;
    if (data.status === 'agrees') { counts.agrees++; counts.matched++; }
    else if (data.status === 'differs') { counts.differs++; counts.matched++; }
    else if (data.status === 'ambiguous') counts.ambiguous++;
    else if (data.status === 'unclassified') counts.unclassified++;
    else if (data.status === 'unavailable') counts.unavailable++;
    else if (data.status === 'expected_behavior') counts.expectedBehavior++;
    else if (data.status === 'no_signal') counts.noSignal++;
  }
  return counts;
}
