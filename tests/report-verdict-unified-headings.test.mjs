import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const box = readFileSync(new URL('../src/lib/components/report/verdict-block.svelte', import.meta.url), 'utf8');
const view = readFileSync(new URL('../src/lib/components/report/report-view.svelte', import.meta.url), 'utf8');

test('minimal review summary presents one purchase-guidance headline with the existing checker status', () => {
	assert.match(box, /const chip = \$derived\(chipFor\(product\)\)/);
	assert.match(box, /const heading = \$derived\(chip\.label\)/);
	assert.match(box, /Review Summary/);
	assert.match(box, /reviewRecommendation\(product\)/);
	assert.match(box, /\{recommendation\.headline\}/);
	assert.match(box, /'verdict-box tone-' \+ visualTone/);
	assert.match(box, /recommendation\.kind === 'caution' \? 'caution'/);
	assert.doesNotMatch(box, /We analyzed \{analyzed\.toLocaleString\(\)\}/);
	assert.doesNotMatch(box, /DeFaketive's assessment/);
	assert.doesNotMatch(box, /What do reviewers say about this product\?/);
	assert.doesNotMatch(box, /No red flags found/);
	assert.doesNotMatch(box, /\{nextStep\}/);
	assert.doesNotMatch(box, /<p class="mt-2 text-sm leading-relaxed text-foreground\/85">/);
});

test('both highlight panels include every available evidence-backed badge', () => {
	assert.match(box, /positiveHighlights\(verdict\.conclusion, Infinity\)/);
	assert.match(box, /What reviewers liked/);
	assert.match(box, /Common concerns/);
	assert.match(box, /Object\.entries\(verdict\.counts \?\? \{\}\)/);
	assert.match(box, /for \(const badge of verdict\.badges \?\? \[\]\)/);
	assert.match(box, /Math\.max\(old\?\.reviews \?\? 0, reviews\)/);
	assert.match(box, /\{#each highlights\.product as item/);
	assert.match(box, /\{#each concerns as item/);
	assert.match(box, /single review may appear under more than one badge/);
	assert.match(box, /Delivery or seller praise is excluded/);
});

test('summary retains conservative wording and advisory disclaimer', () => {
	assert.doesNotMatch(box, /Reported concerns are unverified/);
	assert.match(box, /does not guarantee a product's authenticity, quality, or safety/);
	assert.match(box, /DeFaketive is not 100% accurate/);
	assert.match(box, /final decision to purchase or avoid a product remains the responsibility of the user/);
	assert.doesNotMatch(box, /safe to buy/i);
	assert.doesNotMatch(box, /recommended product/i);
});

test('all report states render conservative guidance without adding a redundant paragraph', () => {
	assert.match(box, /const recommendation = \$derived\(reviewRecommendation\(product\)\)/);
	assert.doesNotMatch(box, /const nextStep =/);
	assert.doesNotMatch(box, /\{nextStep\}/);
	assert.doesNotMatch(box, /\{headline\}/);
});

test('badge counts are readable by screen readers and are never summed', () => {
	assert.match(box, /<span class="sr-only"> \{item\.reviews === 1 \? 'review' : 'reviews'\}<\/span>/);
	assert.doesNotMatch(box, /\.reduce\(/);
	assert.doesNotMatch(box, /concerns\.length\s*\+|\+\s*highlights\.product\.length/);
});

test('explanation modal documents the five-stage panel flow without changing decisions', () => {
  assert.match(view,/Five stages of the product review analysis/);
  const headings=['Product and reviews:','Review sentiment:','What the wording means for this product:','Independent concern checks:','Product conclusion:'];
  const positions=headings.map((heading)=>view.indexOf(`<strong>${heading}</strong>`));
  assert.ok(positions.every((index)=>index>=0),'all five headings are present');
  assert.deepEqual([...positions].sort((a,b)=>a-b),positions,'headings appear in order');
  assert.doesNotMatch(view,/<strong>(?:Product category|Sentiment|Category context|Concern checks|Conclusion):<\/strong>/);
  assert.match(view,/can indicate praise, complaints, or normal use/);
  assert.match(view,/The original sentiment stays in place/);
  assert.match(view,/it never overrides sentiment/);
  assert.match(view,/A positive review can still describe a hazard/);
  assert.match(view,/<p>\{verdict\.detail\}<\/p>/);
  assert.match(view,/This saved report uses an earlier checker version/);
  assert.match(view,/This explanation is based on customer reviews, not independent product testing/);
});

test('explanation control and review navigation remain outside the summary', () => {
	assert.doesNotMatch(box, /How was this result reached\?/);
	assert.match(view, /let explanationOpen = \$state\(false\)/);
	assert.match(view, /Read the \$\{flagged\.length\} flagged reviews/);
	assert.match(view, /How was this result reached\?/);
	assert.match(view, /\(explanationOpen = true\)/);
	assert.match(view, /What do these labels mean\?/);
	assert.match(view, /<Dialog bind:open=\{explanationOpen\}>/);
	assert.match(view, /<p>\{verdict\.detail\}<\/p>/);
});

test('counted flags, server verdict and model behavior are unchanged by this UI-only edit', () => {
	assert.match(view, /const flagged = \$derived\(reviews\.filter/);
	assert.match(view, /<VerdictBlock \{product\} \/>/);
	assert.match(view, /showReviews\('reported'\)/);
});
