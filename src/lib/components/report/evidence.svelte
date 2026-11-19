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
	const activeCount = $derived((filter !== 'all' ? 1 : 0) + (tag ? 1 : 0) + (word ? 1 : 0));
	const sentimentText: Record<string, string> = { positive: 'Positive', negative: 'Negative', uncertain: 'Mixed or unclear', unanalyzed: 'Not analyzed' };
</script>

{#snippet filterControls()}
			<ToggleGroup type="single" variant="outline" value={filter} onValueChange={pickType} aria-label="Filter reviews" class="flex-wrap">
				{#each types as [value, label] (value)}
					<ToggleGroupItem {value}>{label} · {counts[value]}</ToggleGroupItem>
				{/each}
			</ToggleGroup>
{/snippet}

<Card bind:ref={el} id="report-evidence" tabindex={-1} class="scroll-mt-20">
	<CardHeader class="gap-4">
		<div class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Review evidence</p>
				<p class="text-muted-foreground text-sm" aria-live="polite">
					Showing {visible.length} of {filtered.length} matching review{filtered.length === 1 ? '' : 's'}{narrowed ? ` for ${narrowed}` : ''}{ranked ? ', most serious first' : ''}.
				</p>
			</div>
			<InputGroup class="w-full sm:w-64">
				<InputGroupAddon><SearchIcon /></InputGroupAddon>
				<InputGroupInput type="search" placeholder="Filter by word..." autocomplete="off" aria-label="Filter reviews by word" bind:value={query} oninput={() => (limit = 6)} />
			</InputGroup>
		</div>
		<!-- Wide screens: the type buttons sit under the search. Phones: a Filters button opens them from the bottom. -->
		<div class="hidden flex-wrap items-center gap-3 sm:flex">
			{@render filterControls()}
		</div>
		<div class="sm:hidden">
			<Button variant="outline" onclick={() => (sheetOpen = true)}>
				<SlidersHorizontalIcon /> Filters
				{#if activeCount}<Badge variant="secondary">{activeCount}</Badge>{/if}
			</Button>
		</div>
	</CardHeader>
	<CardContent class="grid gap-3">
		{#each visible as review, index (index)}
			{@const reported = reviewTags(review).map((t) => ({ category: t, label: labelNames[t] })).filter((t) => t.label).sort((a, b) => categoryPlace(a.category) - categoryPlace(b.category))}
			{@const matched = [...matchedWords(review).keys()].slice(0, 4)}
			{@const sentiment = sentimentLabel(review)}
			<article class="reveal grid gap-2 rounded-lg border p-4" style="--i:{index % 6}">
				<header class="flex flex-wrap items-center gap-3 text-xs">
					<Stars value={review.rating} />
					<Badge variant="outline">{sentimentText[sentiment] ?? sentiment}</Badge>
					{#if review.time || review.date}<time class="text-muted-foreground">{review.time || review.date}</time>{/if}
				</header>
				<p class="text-sm"><Highlighted pieces={highlightReview(review)} /></p>
				{#if reported.length || matched.length}
					<div class="flex flex-wrap gap-1.5">
						{#each reported as tag (tag.category)}<Badge variant="outline" class="{tag.category === 'safety' && serious ? 'tone-safety' : 'tone-caution'} border-(--tone)/45 bg-(--tone-soft) text-foreground [&>svg]:text-(--tone)">{tag.label}</Badge>{/each}
						{#each matched as text (text)}<Badge variant="secondary">{text}</Badge>{/each}
					</div>
				{/if}
			</article>
		{:else}
			<p class="text-muted-foreground text-sm">No reviews match these filters.</p>
		{/each}
		{#if visible.length < filtered.length}
			<Button variant="outline" class="mx-auto" onclick={() => (limit += 6)}>
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
		<div class="grid gap-4 overflow-y-auto px-4">{@render filterControls()}</div>
		<SheetFooter>
			<Button onclick={() => (sheetOpen = false)}>Show {filtered.length} review{filtered.length === 1 ? '' : 's'}</Button>
		</SheetFooter>
	</SheetContent>
</Sheet>
