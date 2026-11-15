<script lang="ts">
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import Highlighted from '#lib/components/app/highlighted.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import { categoryPlace, segments, view } from '#lib/product.js';
	import type { Badge, Product } from '#lib/types.js';

	let { product, uniqueCount, onread }: { product: Product; uniqueCount: number; onread: (category: string) => void } = $props();
	const badges = $derived([...(view(product).badges ?? [])].sort((a, b) => categoryPlace(a.category) - categoryPlace(b.category)));
	const found = $derived(badges.filter((badge) => badge.mentions > 0));
	const notFound = $derived(badges.filter((badge) => !badge.mentions));
	const safety = $derived(found.some((badge) => badge.category === 'safety'));
	const countText = (n: number) => n === 1 ? '1 review' : String(n) + ' reviews';
</script>

{#snippet result(badge: Badge)}
	{@const quote = badge.evidence?.[0]}
	<div class="grid gap-2 rounded-xl border bg-card p-3 sm:p-4">
		<div class="flex flex-wrap items-start justify-between gap-2">
			<div class="grid gap-0.5">
				<div class="flex items-center gap-2">
					{#if badge.category === 'safety'}
						<TriangleAlertIcon class="size-4 text-destructive" aria-hidden="true" />
					{/if}
					<h4 class="text-sm font-semibold">{badge.label}</h4>
				</div>
				{#if badge.helper}<p class="text-muted-foreground text-xs">{badge.helper}</p>{/if}
			</div>
			<b class="text-sm tabular-nums">{countText(badge.mentions)}</b>
		</div>
		<p class="text-foreground/85 text-sm">{badge.summary}</p>
		{#if badge.category === 'safety' && quote}
			<blockquote class="border-destructive/40 bg-destructive/5 rounded-lg border-l-2 px-3 py-2 text-sm">
				<Highlighted pieces={segments(quote.text, quote.highlights)} />
			</blockquote>
		{:else if quote}
			<details class="group/quote rounded-md bg-muted/40 px-3 py-2">
				<summary class="flex cursor-pointer items-center gap-2 text-xs font-medium [&::-webkit-details-marker]:hidden">
					<ChevronDownIcon class="size-3.5 transition-transform group-open/quote:rotate-180" aria-hidden="true" />
					Read a supporting review
				</summary>
				<blockquote class="text-foreground/85 break-words pt-2 text-sm">
					<Highlighted pieces={segments(quote.text, quote.highlights)} />
				</blockquote>
			</details>
		{/if}
		<Button size="sm" variant="outline" class="w-fit" onclick={() => onread(badge.category)}>
			Read {countText(badge.mentions)} <ArrowRightIcon />
		</Button>
	</div>
{/snippet}

<Card id="report-findings" tabindex={-1} class="gap-4">
	<CardHeader class="gap-1.5">
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Review checks</p>
		<CardTitle class="text-lg">Issues mentioned</CardTitle>
		<CardDescription>
			{#if found.length}
				{found.length} issue {found.length === 1 ? 'type was' : 'types were'} flagged across {uniqueCount} analyzed reviews. Each category counts distinct reviews.
			{:else if badges.length}
				No matching issue reports were flagged in {uniqueCount} analyzed reviews. This does not prove the product has no problems.
			{:else}
				No results from the current checker are available.
			{/if}
		</CardDescription>
	</CardHeader>
	<CardContent class="grid gap-3">
		{#if safety}
			<p class="border-destructive/40 bg-destructive/5 text-destructive flex items-start gap-2 rounded-lg border px-3 py-2 text-sm font-medium">
				<TriangleAlertIcon class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
				Read the reported safety concerns before relying on positive reviews.
			</p>
		{/if}
		{#if found.length}
			<div class="grid gap-3 lg:grid-cols-2">
				{#each found as badge (badge.category)}
					{@render result(badge)}
				{/each}
			</div>
		{/if}
		{#if notFound.length}
			<details class="group/none rounded-lg border bg-muted/30 px-3 py-2">
				<summary class="flex min-h-7 cursor-pointer items-center gap-2 text-sm [&::-webkit-details-marker]:hidden">
					<ChevronDownIcon class="size-4 transition-transform group-open/none:rotate-180" aria-hidden="true" />
					<span>Checks with no matching reports</span>
					<b class="ml-auto tabular-nums">{notFound.length}</b>
				</summary>
				<ul class="grid gap-2 border-t pt-3">
					{#each notFound as badge (badge.category)}
						<li class="flex flex-wrap items-start justify-between gap-2 text-sm">
							<span class="font-medium">{badge.label}</span>
							<span class="text-muted-foreground">{badge.summary}</span>
						</li>
					{/each}
				</ul>
			</details>
		{/if}
		<p class="text-muted-foreground text-xs">Reported concerns are not independently verified; absence of a flag is not a safety guarantee.</p>
	</CardContent>
</Card>
