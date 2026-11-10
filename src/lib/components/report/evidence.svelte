<script lang="ts">
	import SearchIcon from '@lucide/svelte/icons/search';
	import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
	import Highlighted from '#lib/components/app/highlighted.svelte';
	import Stars from '#lib/components/app/stars.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Card, CardContent, CardHeader } from '#lib/components/ui/card/index.js';
	import { InputGroup, InputGroupAddon, InputGroupInput } from '#lib/components/ui/input-group/index.js';
	import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '#lib/components/ui/sheet/index.js';
	import { ToggleGroup, ToggleGroupItem } from '#lib/components/ui/toggle-group/index.js';
	import { categoryPlace, highlightReview, matchedWords, reviewTags, sentimentLabel, seriousness, type EvidenceFilter } from '#lib/product.js';
	import type { Review } from '#lib/types.js';

	let {
		reviews,
		labelNames,
		serious = false,
		checkHref = '',
		analyzeHref = '/scan',
		filter = $bindable<EvidenceFilter>('all'),
		tag = $bindable(''),
		word = $bindable(''),
		query = $bindable(''),
		limit = $bindable(6),
		el = $bindable<HTMLElement | null>(null)
	}: {
		reviews: Review[];
		labelNames: Record<string, string>;
		/** True when this product's safety reports are serious or repeated. Only then are safety tags red. */
		serious?: boolean;
		checkHref?: string;
		analyzeHref?: string;
		filter?: EvidenceFilter;
		tag?: string;
		word?: string;
		query?: string;
		limit?: number;
		el?: HTMLElement | null;
	} = $props();

	const counts = $derived.by(() => {
		const found = { all: reviews.length, reported: 0, negative: 0, uncertain: 0, positive: 0 };
		for (const review of reviews) {
			if (reviewTags(review).length) found.reported += 1;
			const label = sentimentLabel(review);
			if (label in found) found[label as 'negative' | 'uncertain' | 'positive'] += 1;
		}
		return found;
	});

	const filtered = $derived(
		reviews
			.filter((review) => {
				const tags = reviewTags(review);
				const matchesType =
					filter === 'all' || (filter === 'reported' ? tags.length > 0 : sentimentLabel(review) === filter);
				const matchesTag = !tag || tags.includes(tag);
				const matchesWord = !word || matchedWords(review).has(word);
				const needle = query.trim().toLowerCase();
				return matchesType && matchesTag && matchesWord && (!needle || String(review.content ?? '').toLowerCase().includes(needle));
			})
			// Most serious first, so one safety report is not buried under seventy other reviews. Ties keep their order.
			.sort((a, b) => seriousness(a) - seriousness(b))
	);
	// Worth saying only when the list really was reordered: more than one review, and at least one reports a problem.
	const ranked = $derived(filtered.length > 1 && reviewTags(filtered[0]).length > 0);
	const visible = $derived(filtered.slice(0, limit));
	const narrowed = $derived(
		[tag ? `“${labelNames[tag] ?? tag}”` : '', word ? `“${word}”` : ''].filter(Boolean).join(', ')
	);

	const types: [EvidenceFilter, string][] = [
		['all', 'All'],
		['reported', 'Flagged'],
		['negative', 'Negative'],
		['uncertain', 'Mixed or unclear'],
		['positive', 'Positive']
	];

	function pickType(value: string) {
		// The chip that is already on switches itself off; keep one chip on.
		if (!value) return;
		filter = value as EvidenceFilter;
		tag = '';
		// "All" clears every narrowing, including a picked word and the search box.
		if (filter === 'all') {
			word = '';
			query = '';
		}
		limit = 6;
	}
	let sheetOpen = $state(false);
	const activeCount = $derived((filter !== 'all' ? 1 : 0) + (tag ? 1 : 0) + (word ? 1 : 0) + (query.trim() ? 1 : 0));
	const sentimentText: Record<string, string> = { positive: 'Positive', negative: 'Negative', uncertain: 'Mixed or unclear', unanalyzed: 'Not analyzed' };
	const aspectNames: Record<string, string> = { delivery: 'Delivery', packaging: 'Packaging', seller_service: 'Seller service', price: 'Price', quality: 'Quality', functionality: 'Functionality' };
	const learnedLabels: Record<string, string> = { positive: 'Positive opinion', negative: 'Negative opinion', neutral: 'Neutral opinion', mixed: 'Both positive and negative opinions' };
	function modelScore(value: number | null | undefined): string {
		return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'Unavailable';
	}
</script>

{#snippet filterControls()}
			<ToggleGroup type="single" variant="outline" spacing={2} value={filter} onValueChange={pickType} aria-label="Filter reviews" class="max-w-full flex-wrap">
				{#each types as [value, label] (value)}
					<ToggleGroupItem {value} class="h-auto min-h-11 whitespace-normal px-3 py-2">{label} · {counts[value]}</ToggleGroupItem>
				{/each}
			</ToggleGroup>
{/snippet}

<Card bind:ref={el} id="report-evidence" tabindex={-1} aria-labelledby="evidence-heading" class="min-w-0 scroll-mt-20 [overflow-wrap:anywhere]">
	<CardHeader class="gap-4">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h2 id="evidence-heading" class="text-xl font-semibold">Review evidence</h2>
				<p class="text-muted-foreground text-sm" aria-live="polite">
					Showing {visible.length} of {filtered.length} matching review{filtered.length === 1 ? '' : 's'}{narrowed ? ` for ${narrowed}` : ''}{ranked ? ', most serious first' : ''}.
				</p>
			</div>
			<InputGroup class="min-h-11 w-full sm:w-64">
				<InputGroupAddon><SearchIcon /></InputGroupAddon>
				<InputGroupInput type="search" placeholder="Filter by word..." autocomplete="off" aria-label="Filter reviews by word" bind:value={query} oninput={() => (limit = 6)} />
			</InputGroup>
		</div>
		<!-- Wide screens: the type buttons sit under the search. Phones: a Filters button opens them from the bottom. -->
		<div class="hidden flex-wrap items-center gap-3 sm:flex">
			{@render filterControls()}
		</div>
		<div class="sm:hidden">
			<Button variant="outline" class="min-h-11" aria-haspopup="dialog" aria-expanded={sheetOpen} onclick={() => (sheetOpen = true)}>
				<SlidersHorizontalIcon /> Filters
				{#if activeCount}<Badge variant="secondary">{activeCount}</Badge>{/if}
			</Button>
		</div>
		{#if activeCount}
			<div class="flex flex-wrap items-center gap-2">
				<p class="text-muted-foreground text-sm">{activeCount} active filter{activeCount === 1 ? '' : 's'}{narrowed ? `: ${narrowed}` : ''}</p>
				<Button variant="outline" class="h-auto min-h-11 whitespace-normal" onclick={() => pickType('all')}>Clear all filters</Button>
			</div>
		{/if}
	</CardHeader>
	<CardContent class="grid gap-3">
		{#each visible as review, index (index)}
			{@const reported = reviewTags(review).map((t) => ({ category: t, label: labelNames[t] })).filter((t) => t.label).sort((a, b) => categoryPlace(a.category) - categoryPlace(b.category))}
			{@const matched = [...matchedWords(review).keys()].slice(0, 4)}
			{@const sentiment = sentimentLabel(review)}
			{@const learnedAspects = Object.entries(review.sentiment_analysis?.aspect_sentiment_learned ?? {})}
			{@const mixed = review.sentiment_analysis?.sentiment_extra?.mixed}
			<article class="reveal grid min-w-0 gap-2 rounded-lg border p-3 sm:p-4 [&_[data-slot=badge]]:max-w-full [&_[data-slot=badge]]:whitespace-normal" style="--i:{index % 6}" aria-label="Review {index + 1}">
				<header class="flex flex-wrap items-center gap-3 text-xs">
					<Stars value={review.rating} />
					<Badge variant="outline">{review.sentiment_analysis?.label?.toLowerCase() === 'neutral' ? 'Neutral' : sentimentText[sentiment] ?? sentiment}</Badge>
					{#if review.time || review.date}<time class="text-muted-foreground">{review.time || review.date}</time>{/if}
				</header>
				<p class="text-sm"><Highlighted pieces={highlightReview(review)} /></p>
				{#if review.sentiment_analysis?.aspect_sentiment?.evidence?.length}
					<details class="rounded-md bg-muted/40 p-3 text-sm">
						<summary class="min-h-11 cursor-pointer rounded-sm py-3 font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring">Opinions by topic · Preview{review.sentiment_analysis.aspect_sentiment.mixed_evidence ? ' · Mixed opinions' : ''}</summary>
						<p class="text-muted-foreground mt-2 text-xs">Rule-based topic labels with exact review quotes. They do not change safety or defect warnings.</p>
						<ul class="mt-2 grid gap-2">
							{#each review.sentiment_analysis.aspect_sentiment.evidence as item, i (i)}
								<li><span class="font-medium">{aspectNames[item.aspect] ?? item.aspect}: {item.label}</span><blockquote class="mt-1"><mark class="bg-warning/20 text-foreground rounded px-1">{item.text}</mark></blockquote></li>
							{/each}
						</ul>
					</details>
				{/if}
				{#if learnedAspects.length || mixed}
					<details class="rounded-md border p-3 text-sm" data-testid="learned-sentiment">
						<summary class="min-h-11 cursor-pointer rounded-sm py-3 font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring">Experimental AI sentiment predictions</summary>
						<p class="text-muted-foreground mt-2 text-xs">These are learned model predictions, not exact quote evidence. Scores are not calibrated accuracy. They do not change the overall sentiment label or safety and defect warnings. Neutral and mixed are distinct: mixed predicts both positive and negative opinions.</p>
						{#if mixed}
							<p class="mt-2" data-testid="mixed-prediction">Mixed opinions: {mixed.detected === true ? 'Predicted' : mixed.detected === false ? 'Not predicted' : 'Unavailable'}</p>
						{/if}
						{#if learnedAspects.length}
							<ul class="mt-2 grid gap-2">
								{#each learnedAspects as [aspect, prediction] (aspect)}
									<li><span class="font-medium">{aspectNames[aspect] ?? aspect}: {learnedLabels[prediction.label] ?? prediction.label}</span></li>
								{/each}
							</ul>
						{/if}
						<details class="mt-3 rounded-md bg-muted/40 p-3" data-testid="learned-technical">
							<summary class="min-h-11 cursor-pointer rounded-sm py-3 font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring">Technical details</summary>
							<p class="text-muted-foreground text-xs">Raw model scores are uncalibrated and do not measure accuracy or certainty.</p>
							{#if mixed}<p class="mt-2">Mixed opinions model score: {modelScore(mixed.probability)}</p>{/if}
							<ul class="mt-2 grid gap-2">
								{#each learnedAspects as [aspect, prediction] (aspect)}
									<li>{aspectNames[aspect] ?? aspect}: <span class="text-muted-foreground">Polarity model score: {modelScore(prediction.confidence)}; Topic mention model score: {modelScore(prediction.mention_probability)}</span></li>
								{/each}
							</ul>
						</details>
					</details>
				{/if}
				{#if reported.length || matched.length}
					<div class="flex flex-wrap gap-1.5">
						{#each reported as tag (tag.category)}<Badge variant="outline" class="{tag.category === 'safety' && serious ? 'tone-safety' : 'tone-caution'} border-(--tone)/45 bg-(--tone-soft) text-foreground [&>svg]:text-(--tone)">{tag.label}</Badge>{/each}
						{#each matched as text (text)}<Badge variant="secondary">{text}</Badge>{/each}
					</div>
				{/if}
			</article>
		{:else}
			<div class="grid justify-items-start gap-3 rounded-lg border p-4">
				{#if reviews.length}
					<p class="text-sm">No reviews match these filters. Clear them to see all available reviews.</p>
					<Button variant="outline" onclick={() => pickType('all')}>Clear all filters</Button>
				{:else}
					<p class="text-sm">No review text is available in this report. Check another listing{checkHref ? ', or check this product again' : ''}.</p>
					<div class="flex flex-wrap gap-2">
						{#if checkHref}<Button variant="outline" href={checkHref}>Check this product again</Button>{/if}
						<Button variant="outline" href={analyzeHref}>Check another product</Button>
					</div>
				{/if}
			</div>
		{/each}
		{#if visible.length < filtered.length}
			<Button variant="outline" class="mx-auto h-auto min-h-11 max-w-full whitespace-normal" onclick={() => (limit += 6)}>
				View {Math.min(6, filtered.length - visible.length)} more reviews
			</Button>
		{/if}
	</CardContent>
</Card>

<Sheet bind:open={sheetOpen}>
	<SheetContent side="bottom" class="max-h-[85svh] rounded-t-xl">
		<SheetHeader>
			<SheetTitle>Filter reviews</SheetTitle>
			<SheetDescription>Pick a kind of review.</SheetDescription>
		</SheetHeader>
		<div class="grid min-h-0 gap-4 overflow-y-auto px-4">
			{@render filterControls()}
			{#if activeCount}<Button variant="outline" class="min-h-11" onclick={() => pickType('all')}>Clear all filters</Button>{/if}
		</div>
		<SheetFooter>
			<Button class="h-auto min-h-11 whitespace-normal" onclick={() => (sheetOpen = false)}>Show {filtered.length} review{filtered.length === 1 ? '' : 's'}</Button>
		</SheetFooter>
	</SheetContent>
</Sheet>
