import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const box = readFileSync(new URL('../src/lib/components/report/verdict-block.svelte', import.meta.url), 'utf8');
const view = readFileSync(new URL('../src/lib/components/report/report-view.svelte', import.meta.url), 'utf8');

test('all verdict states use one question heading and keep a single visible severity label', () => {
	assert.match(box, /const heading = \$derived\(chip\.label\)/);
	assert.match(box, /<span>\{heading\}<\/span>/);
	assert.match(box, /What do reviewers say about this product\?/);
	assert.doesNotMatch(box, /No red flags found/);
	assert.doesNotMatch(box, /\{chip\.kind === 'clear' \? 'What do reviewers/);
	assert.doesNotMatch(box, /\{verdict\.headline\}/);
	assert.doesNotMatch(box, /· What reviewers report/);
	assert.doesNotMatch(box, /<h3[^>]*>Quick review summary<\/h3>/);
});

test('dangerous or uncertain checker details remain prominent', () => {
	assert.match(box, /\{#if verdict\.detail && chip\.kind !== 'clear'\}/);
	assert.match(box, /<p class="mt-2 text-sm leading-relaxed text-foreground\/85">\{verdict\.detail\}<\/p>/);
	assert.match(box, /aria-label="Quick review summary"/);
	assert.match(box, /\{guidance\.text\}/);
	assert.match(box, /DeFaketive is not 100% accurate/);
});

test('explanation control lives with review actions and opens the real checker detail', () => {
	assert.doesNotMatch(box, /How was this result reached\?/);
	assert.match(view, /let explanationOpen = \$state\(false\)/);
	const actionStart = view.indexOf('<!-- One thing to do next, chosen by the verdict.');
	const actionEnd = view.indexOf('<!-- The numbers behind the report.', actionStart);
	const action = view.slice(actionStart, actionEnd);
	assert.match(action, /Read the \$\{flagged\.length\} flagged reviews/);
	assert.match(action, /How was this result reached\?/);
	assert.match(action, /\(explanationOpen = true\)/);
	assert.match(action, /What do these labels mean\?/);
	assert.match(view, /<Dialog bind:open=\{explanationOpen\}>/);
	assert.match(view, /<p>\{verdict\.detail\}<\/p>/);
});

test('counted flags, result severity and models are not changed by this UI-only PR', () => {
	assert.match(view, /const flagged = \$derived\(reviews\.filter/);
	assert.match(view, /<VerdictBlock \{product\} \/>/);
	assert.match(view, /showReviews\('reported'\)/);
});
