<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import { positiveHighlights, reviewMentionCount } from '#lib/positive-highlights.js';
	import type { Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	// Only review-grounded positive aspects: count each distinct review once.
	// This is not a product recommendation or independent safety assurance.
	let { product }: { product: Product } = $props();
	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const highlights = $derived(positiveHighlights(verdict.conclusion));
	const analyzed = $derived(Number(verdict.reviews_analyzed) || highlights.reviewed || 0);
	const reported = $derived((verdict.badges ?? []).filter((item) => Number(item.mentions) > 0));
	const important = $derived(reported.filter((item) => !item.informs_only));
	const caution = $derived(chip.kind === 'caution' || chip.kind === 'safety');
	const first = $derived(highlights.product[0]);
	const explanation = $derived(
		first
			? 'Most often praised: ' + first.label.toLowerCase() + ', mentioned positively in ' + reviewMentionCount(first.reviews) + '.'
			: 'Only positive qualities explicitly supported by review text appear here.'
	);
</script>

{#key product.link}
	<section
		class="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-xs"
		aria-label="Review highlights"
	>
		<div class="grid min-w-0 gap-4 p-4 sm:p-5 md:grid-cols-[minmax(0,1fr)_minmax(12rem,15rem)] md:gap-6">
			<div class="grid min-w-0 content-start gap-3">
				<div class="flex flex-wrap items-center gap-2 text-sm font-semibold">
					<CircleCheckIcon class="size-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
					<h2 class="font-semibold">What reviewers liked</h2>
					<span class="text-muted-foreground font-normal">· positive review themes</span>
				</div>

				{#if highlights.product.length}
					<div class="flex flex-wrap items-start gap-2" aria-label="Positive product qualities and support counts">
						{#each highlights.product as item (item.key)}
							<details class="group/highlight min-w-0 max-w-full rounded-lg border border-emerald-700/25 bg-emerald-500/5 px-3 py-2">
								<summary class="flex min-h-6 cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 text-sm [&::-webkit-details-marker]:hidden">
									<b class="break-words font-semibold">{item.label}</b>
									<span class="text-muted-foreground shrink-0 text-xs">{reviewMentionCount(item.reviews)}</span>
									<ChevronDownIcon class="text-muted-foreground size-3.5 shrink-0 transition-transform group-open/highlight:rotate-180" aria-hidden="true" />
								</summary>
								<div class="grid max-w-sm gap-2 border-t border-emerald-700/20 pt-2 text-xs">
									<p class="text-muted-foreground">{reviewMentionCount(item.reviews)} explicitly praised this aspect.</p>
									{#if item.concerns}
										<p class="text-amber-700 dark:text-amber-400">Also criticised in {reviewMentionCount(item.concerns)}.</p>
									{/if}
									{#each item.quotes as quote, index (index)}
										<q class="text-foreground/85 block break-words border-l-2 border-emerald-600/40 pl-2">{quote}</q>
									{/each}
								</div>
							</details>
						{/each}
					</div>
					<p class="text-foreground/80 text-sm">{explanation}</p>
				{:else}
					<p class="text-foreground/80 text-sm">No specific positive product quality could be reliably identified from the available review text.</p>
				{/if}

				{#if highlights.service.length}
					<p class="text-muted-foreground text-xs">
						Delivery or seller praise is separate: {highlights.service[0].label.toLowerCase()} ({reviewMentionCount(highlights.service[0].reviews)}).
						It does not establish product quality.
					</p>
				{/if}
				<p class="text-muted-foreground text-xs">
					Based on {analyzed} analyzed review{analyzed === 1 ? '' : 's'}. Theme counts refer to distinct reviews; a review can mention several qualities.
				</p>
			</div>

			<aside class="grid content-start gap-2 rounded-lg border border-border/80 bg-muted/40 p-3" aria-label="Checker status">
				<div class="flex items-center gap-2 text-xs font-semibold tracking-wide uppercase">
					{#if chip.kind === 'safety'}
						<TriangleAlertIcon class="size-4 text-destructive" aria-hidden="true" />
					{:else if caution}
						<CircleAlertIcon class="size-4 text-amber-600" aria-hidden="true" />
					{:else if chip.kind === 'clear'}
						<CircleCheckIcon class="size-4 text-emerald-600" aria-hidden="true" />
					{:else}
						<CircleHelpIcon class="size-4 text-muted-foreground" aria-hidden="true" />
					{/if}
					<span>Review checks</span>
				</div>
				<p class={cn('text-sm font-semibold', chip.kind === 'safety' && 'text-destructive')}>{verdict.headline}</p>
				<p class="text-muted-foreground text-xs">{verdict.detail}</p>
				{#if important.length}
					<ul class="grid gap-1.5 text-xs">
						{#each important.slice(0, 3) as item (item.category)}
							<li class="flex items-start justify-between gap-2 rounded-md bg-background/70 px-2 py-1.5">
								<span>{item.label}</span>
								<b class="shrink-0 tabular-nums">{reviewMentionCount(item.mentions)}</b>
							</li>
						{/each}
					</ul>
				{/if}
				<p class="text-muted-foreground text-xs">Review reports are signals, not independent proof of safety or authenticity.</p>
			</aside>
		</div>

		{#if caution}
			<p class={cn('border-t px-4 py-3 text-sm sm:px-5', chip.kind === 'safety' ? 'border-destructive/30 bg-destructive/5 text-destructive' : 'border-amber-500/30 bg-amber-500/5')}>
				<strong>Check the flagged reviews before buying.</strong>
				Positive feedback does not cancel reported safety, authenticity or defect concerns.
			</p>
		{/if}
	</section>
{/key}
