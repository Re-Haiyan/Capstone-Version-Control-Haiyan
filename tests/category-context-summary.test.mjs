import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { categoryContextSummary } from '../src/lib/category-context-summary.js';

const review = (status, opts = {}) => ({
  included_in_analysis: opts.included_in_analysis ?? true,
  sentiment_analysis: { sentiment: { category_context: {
    revision: opts.revision ?? 'category-context-v1',
    status, used_for_decision: opts.used_for_decision ?? false,
    sentiment_overridden: opts.sentiment_overridden ?? false
  }}}
});

test('counts backend contextual evidence without interpreting mismatches as model errors', () => {
  assert.deepEqual(categoryContextSummary({comments:[
    review('agrees'), review('differs'), review('ambiguous'), review('no_signal'),
    review('unclassified'), review('agrees', {included_in_analysis:false})
  ]}), {
    checked:5,agrees:1,differs:1,ambiguous:1,noSignal:1,unclassified:1,matched:2,expectedBehavior:0,unavailable:0
  });
});

test('v2 expected features are not counted as positive or negative corrections', () => {
  const summary = categoryContextSummary({comments:[
    review('expected_behavior', {revision:'category-context-v2'}),
    review('agrees', {revision:'category-context-v2'}),
    review('differs', {revision:'category-context-v2.1'}),
    review('unavailable', {revision:'category-context-v2'})
  ]});
  assert.equal(summary.checked,4);
  assert.equal(summary.expectedBehavior,1);
  assert.equal(summary.matched,2);
  assert.equal(summary.unavailable,1);
});

test('unknown statuses never inflate the number of contextual checks', () => {
  const result = categoryContextSummary({comments:[
    review('totally_new_status', {revision:'category-context-v2'}),
    review(null, {revision:'category-context-v2'}),
    review('expected_behavior', {revision:'category-context-v2'}),
    review('no_signal', {revision:'category-context-v2'})
  ]});
  assert.equal(result.checked, 2);
  assert.equal(result.noSignal, 1);
  assert.equal(result.expectedBehavior, 1);
});

test('old reports and unsafe/unknown metadata never invent a completed check', () => {
  assert.equal(categoryContextSummary(null).checked,0);
  assert.equal(categoryContextSummary({comments:[{},review('differs',{revision:'unknown'}),review('agrees',{used_for_decision:true}),review('differs',{sentiment_overridden:true})]}).checked,0);
});

test('shopper summary shows the recommendation and category, not research diagnostics', () => {
  const file=readFileSync(new URL('../src/lib/components/report/verdict-block.svelte',import.meta.url),'utf8');
  assert.match(file,/reviewRecommendation\(product\)/);
  assert.match(file,/const verdict = \$derived\(view\(product\)\)/);
  assert.match(file,/data-product-category/);
  assert.match(file,/What reviewers liked/);
  assert.match(file,/Common concerns/);
  assert.match(file,/DeFaketive is not 100% accurate/);
  assert.doesNotMatch(file,/data-category-context-summary/);
  assert.doesNotMatch(file,/How product context was checked/);
  assert.doesNotMatch(file,/contextualChecks/);
  assert.doesNotMatch(file,/categoryContextSummary\(product\)/);
  assert.doesNotMatch(file,/No explicit category-specific praise or complaint examples matched/);
});

test('category context metadata processing remains available for developer audit', () => {
  const code=readFileSync(new URL('../src/lib/category-context-summary.js', import.meta.url), 'utf8');
  assert.match(code, /category_context/);
  assert.match(code, /sentiment_overridden/);
  assert.match(code, /expected_behavior/);
});

