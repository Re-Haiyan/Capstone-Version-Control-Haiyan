// Compare the actual shopper guidance and highlights using private paired replay files.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { reviewRecommendation } from '../src/lib/review-recommendation.js';
import { positiveHighlights } from '../src/lib/positive-highlights.js';
const evidence = process.argv[2];
const read = name => JSON.parse(fs.readFileSync(path.join(evidence, name), 'utf8'));
const sets = [['baseline', 'candidate'], ['baseline-live', 'candidate-live'], ['baseline-additional', 'candidate-additional']];
const changes = []; let reports = 0; let quotes = 0;
for (const [before, after] of sets) {
  const left = read(before + '-reports-private.json');
  const right = read(after + '-reports-private.json');
  assert.equal(left.length, right.length);
  for (let i = 0; i < left.length; i++) {
    const a = left[i], b = right[i];
    assert.equal(a.index, b.index); assert.equal(a.input_sha256, b.input_sha256);
    const recommendation = r => reviewRecommendation({ ...r.fresh, badge_view: r.view, checked_with_current: true });
    const old = recommendation(a), fresh = recommendation(b);
    if (old.kind !== fresh.kind || old.headline !== fresh.headline) changes.push({set: after, index: b.index, before: old, after: fresh});
    const highlights = positiveHighlights(b.view.conclusion, Infinity);
    for (const item of [...highlights.product, ...highlights.service]) for (const quote of item.quotes) {
      assert(b.fresh.comments.some(r => String(r.content || '').includes(quote.replace(/…$/, ''))), 'Ungrounded highlight');
      quotes++;
    }
    if (Number(b.view.counts?.safety) > 0) assert.notEqual(fresh.kind, 'consider', 'Safety suppressed in shopper guidance');
    reports++;
  }
}
const result = {reports, grounded_highlight_quotes: quotes, guidance_changes: changes};
fs.writeFileSync(path.join(evidence, 'shopper-guidance.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
