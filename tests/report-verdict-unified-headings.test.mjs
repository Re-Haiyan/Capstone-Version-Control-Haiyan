import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const box = readFileSync(new URL('../src/lib/components/report/verdict-block.svelte', import.meta.url), 'utf8');
const view = readFileSync(new URL('../src/lib/components/report/report-view.svelte', import.meta.url), 'utf8');

test('a single minimal summary uses the existing severity classification', () => {
	assert.match(box, /const chip = \$derived\(chipFor\(product\)\)/);
	assert.match(box, /const heading = \$derived\(chip\.label\)/);
	assert.match(box, /Review Summary/);
	assert.match(box, /A possible safety concern was reported/);
	assert.match(box, /No warning-level concerns were detected/);
	assert.match(box, /We analyzed \{analyzed\.toLocaleString\(\)\}/);
	assert.doesNotMatch(box, /DeFaketive's assessment/);
	assert.doesNotMatch(box, /What do reviewers say about this product\?/);
	assert.doesNotMatch(box, /No red flags found/);
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
	assert.match(box, /Reported concerns are unverified/);
	assert.match(box, /does not guarantee the product is safe, authentic, or reliable/);
	assert.match(box, /DeFaketive is not 100% accurate/);
	assert.match(box, /final decision to purchase or avoid a product remains the responsibility of the user/);
	assert.doesNotMatch(box, /safe to buy/i);
	assert.doesNotMatch(box, /recommended product/i);
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
