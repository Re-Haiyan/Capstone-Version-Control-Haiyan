<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import { positiveHighlights, reviewMentionCount } from '#lib/positive-highlights.js';
	import type { Product } from '#lib/types.js';

	// The card only arranges existing review-backed evidence. Never infer
	// a safety guarantee, recommendation, or independent product verdict.
	let { product }: { product: Product } = $props();
	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const highlights = $derived(positiveHighlights(verdict.conclusion));
	const analyzed = $derived(Number(verdict.reviews_analyzed) || highlights.reviewed || 0);
	const reported = $derived(
		(verdict.badges ?? [])
			.filter((item) => Number(item.mentions) > 0)
			.sort((a, b) =>
				(a.category === 'safety' ? -1 : b.category === 'safety' ? 1 : 0)
				|| Number(b.mentions) - Number(a.mentions)
			)
	);
	const safetyMentioned = $derived(reported.some((item) => item.category === 'safety'));
	const serious = $derived(safetyMentioned || chip.kind === 'safety' || chip.kind === 'caution');
	const belowWarning = $derived(reported.length > 0 && chip.kind === 'clear' && !safetyMentioned);
	const checkerStatus = $derived(
		safetyMentioned || chip.kind === 'safety'
			? 'Safety concern'
			: chip.kind === 'caution'
				? 'Warning-level concerns'
				: belowWarning
					? 'Below warning level'
					: chip.kind === 'clear'
						? 'No warning-level flags'
						: 'Status uncertain'
	);
	const checkerExplanation = $derived(
		safetyMentioned
			? 'At least one review mentions a safety issue. Read the supporting reviews.'
			: chip.kind === 'safety' || chip.kind === 'caution'
				? 'These reports require closer attention before buying.'
				: belowWarning
					? 'Issues were reported, but did not reach the checker’s warning threshold.'
					: chip.kind === 'clear'
						? 'The checker found no warning-level concerns in this sample.'
						: 'There is not enough evidence for a reliable checker status.'
	);
</script>

{#key product.link}
	<section class="min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-xs" aria-label="Review highlights">
		<header class="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 px-4 py-3 sm:px-5">
			<h2 class="text-sm font-semibold">Review highlights</h2>
			<span class="text-muted-foreground text-xs tabular-nums">
				{analyzed} analyzed review{analyzed === 1 ? '' : 's'}
			</span>
		</header>

		<div class="grid min-w-0 md:grid-cols-2">
			<div class="min-w-0 space-y-3 px-4 py-4 sm:px-5">
				<div class="flex items-start gap-2">
					{#if highlights.product.length}
						<CircleCheckIcon class="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
					{:else}
						<CircleHelpIcon class="text-muted-foreground mt-0.5 size-4 shrink-0" aria-hidden="true" />
					{/if}
					<div class="min-w-0">
						<h3 class="text-sm font-semibold">What reviewers liked</h3>
						<p class="text-muted-foreground text-xs">Positive qualities found in review text</p>
					</div>
				</div>

				{#if highlights.product.length}
					<div class="flex flex-wrap items-start gap-2" aria-label="Supported positive product qualities">
						{#each highlights.product as item (item.key)}
							<details class="group/highlight min-w-0 max-w-full rounded-lg border border-emerald-600/25 bg-emerald-500/5">
								<summary class="flex min-h-9 cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-1 px-3 py-1.5 text-sm [&::-webkit-details-marker]:hidden">
									<span class="break-words font-medium">{item.label}</span>
									<span class="text-muted-foreground shrink-0 text-xs tabular-nums">{reviewMentionCount(item.reviews)}</span>
									<ChevronDownIcon class="text-muted-foreground size-3.5 shrink-0 transition-transform group-open/highlight:rotate-180" aria-hidden="true" />
								</summary>
								<div class="max-w-sm space-y-2 border-t border-emerald-600/20 px-3 py-2 text-xs">
									{#if item.concerns}
										<p class="text-amber-700 dark:text-amber-400">
											Also criticised in {reviewMentionCount(item.concerns)}.
										</p>
									{/if}
									{#if item.quotes.length}
										{#each item.quotes as quote, index (index)}
											<q class="block break-words border-l-2 border-emerald-600/40 pl-2 text-foreground/85">{quote}</q>
										{/each}
									{:else}
										<p class="text-muted-foreground">Supported by {reviewMentionCount(item.reviews)}; no excerpt available.</p>
									{/if}
								</div>
							</details>
						{/each}
					</div>
				{:else}
					<p class="text-muted-foreground text-sm">
						No specific positive product qualities were identified in the available review text.
					</p>
				{/if}

				{#if highlights.service.length}
					<p class="text-muted-foreground text-xs">
						Seller or delivery praise is separate:
						{highlights.service[0].label.toLowerCase()} ({reviewMentionCount(highlights.service[0].reviews)}).
					</p>
				{/if}
			</div>

			<div class="min-w-0 space-y-3 border-t border-border/70 bg-muted/20 px-4 py-4 sm:px-5 md:border-l md:border-t-0">
				<div class="flex flex-wrap items-start justify-between gap-2">
					<div class="flex items-start gap-2">
						{#if safetyMentioned || chip.kind === 'safety'}
							<TriangleAlertIcon class="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
						{:else if serious || belowWarning}
							<CircleAlertIcon class="mt-0.5 size-4 shrink-0 text-amber-600" aria-hidden="true" />
						{:else if chip.kind === 'clear'}
							<CircleCheckIcon class="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
						{:else}
							<CircleHelpIcon class="text-muted-foreground mt-0.5 size-4 shrink-0" aria-hidden="true" />
						{/if}
						<div class="min-w-0">
							<h3 class="text-sm font-semibold">Issues reviewers reported</h3>
							<p class="text-muted-foreground text-xs">Grouped by type of concern</p>
						</div>
					</div>
					<span class={safetyMentioned || chip.kind === 'safety'
						? 'rounded-full border border-destructive/30 bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive'
						: serious || belowWarning
							? 'rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-800 dark:text-amber-300'
							: 'rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground'}>
						{checkerStatus}
					</span>
				</div>

				{#if reported.length}
					<ul class="grid gap-2 text-sm" aria-label="Types of issues reported and distinct review counts">
						{#each reported as item (item.category)}
							<li class="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/80 px-3 py-2">
								<span class="min-w-0 break-words font-medium">{item.label}</span>
								<span class="text-muted-foreground shrink-0 text-xs tabular-nums">{reviewMentionCount(item.mentions)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-muted-foreground text-sm">No matching issue reports were flagged in the analyzed sample.</p>
				{/if}
				<p class={safetyMentioned || chip.kind === 'safety'
					? 'text-xs font-medium text-destructive'
					: 'text-muted-foreground text-xs'}>
					{checkerExplanation}
				</p>
			</div>
		</div>

		<footer class="border-t border-border/70 px-4 py-2.5 text-xs text-muted-foreground sm:px-5">
			Counts represent reviews, not verified incidents. One review may mention multiple qualities or issues.
			Review reports do not prove a product is safe or unsafe.
		</footer>
	</section>
{/key}
