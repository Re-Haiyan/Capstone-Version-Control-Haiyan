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

	// Restore the familiar full-width, color-coded checker verdict. The new
	// positive qualities panel is independent and can never reduce or replace
	// the warning. No model, threshold or saved-review changes are made here.
	let { product }: { product: Product } = $props();
	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const highlights = $derived(positiveHighlights(verdict.conclusion, 3));
	const analyzed = $derived(Number(verdict.reviews_analyzed) || highlights.reviewed || 0);
	const safetyReported = $derived(
		(verdict.badges ?? []).some((item) => item.category === 'safety' && Number(item.mentions) > 0)
	);
	const showWarning = $derived(chip.kind === 'safety' || chip.kind === 'caution' || safetyReported);
	const resultLabel = $derived(
		chip.kind === 'safety' ? 'Safety warning'
			: chip.kind === 'caution' || safetyReported ? 'Caution'
			: chip.kind === 'clear' ? 'Review check' : 'Review status'
	);
</script>

{#key product.link}
	<div class="grid min-w-0 gap-3">
		<!-- Keep the original result as the visually dominant, full-width card. -->
		<section class={cn(
			'verdict-box tone-' + (safetyReported && chip.kind === 'clear' ? 'caution' : chip.kind),
			'min-w-0 rounded-xl border-2 border-(--tone)/60 bg-(--tone-soft) p-4 text-foreground shadow-xs [overflow-wrap:anywhere] sm:p-5'
		)} aria-label="Review checker result">
			<div class="flex flex-wrap items-center gap-2 text-sm font-medium">
				{#if chip.kind === 'safety'}
					<TriangleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else if showWarning}
					<CircleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else if chip.kind === 'clear'}
					<CircleCheckIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else}
					<CircleHelpIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{/if}
				<span>{resultLabel}</span>
				<span class="text-muted-foreground font-normal">· What reviewers report</span>
			</div>
			<h2 class="mt-2 text-xl font-semibold leading-snug tracking-tight sm:text-2xl">{verdict.headline}</h2>
			{#if verdict.detail}
				<p class="mt-2 text-sm text-foreground/85">{verdict.detail}</p>
			{/if}
			<p class="mt-2 text-xs text-muted-foreground">Review signals are a guide, not proof.</p>
		</section>

		<!-- Compact, supplementary themes. Never invent positive claims. -->
		<section class="min-w-0 rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5" aria-label="What reviewers liked">
			<div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
				<div class="flex items-center gap-2">
					{#if highlights.product.length}
						<CircleCheckIcon class="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
					{:else}
						<CircleHelpIcon class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
					{/if}
					<h3 class="text-sm font-semibold">What reviewers liked</h3>
				</div>
				<span class="text-xs text-muted-foreground tabular-nums">{analyzed} analyzed review{analyzed === 1 ? '' : 's'}</span>
			</div>
			<p class="mt-1 text-xs text-muted-foreground">Positive product qualities</p>

			{#if highlights.product.length}
				<div class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
					{#each highlights.product as item (item.key)}
						<details class="group/quality min-w-0 rounded-lg border border-emerald-600/25 bg-emerald-500/5">
							<summary class="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-sm [&::-webkit-details-marker]:hidden">
								<span class="min-w-0 break-words font-medium">{item.label}</span>
								<span class="flex shrink-0 items-center gap-1 text-xs tabular-nums text-muted-foreground">
									{reviewMentionCount(item.reviews)}
									<ChevronDownIcon class="size-3.5 transition-transform group-open/quality:rotate-180" aria-hidden="true" />
								</span>
							</summary>
							<div class="grid gap-2 border-t border-emerald-600/20 px-3 py-2 text-xs">
								{#if item.concerns}
									<p class="text-amber-700 dark:text-amber-400">Also criticised in {reviewMentionCount(item.concerns)}.</p>
								{/if}
								{#if item.quotes.length}
									{#each item.quotes as quote, index (index)}
										<q class="block break-words border-l-2 border-emerald-600/40 pl-2 text-foreground/85">{quote}</q>
									{/each}
								{:else}
									<p class="text-muted-foreground">No review excerpt available.</p>
								{/if}
							</div>
						</details>
					{/each}
				</div>
			{:else}
				<p class="mt-3 text-sm text-muted-foreground">No specific positive product qualities could be identified from the available review text.</p>
			{/if}

			<p class="mt-3 text-xs text-muted-foreground">
				{#if highlights.service.length}
					Delivery or seller praise is separate: {highlights.service[0].label.toLowerCase()}
					({reviewMentionCount(highlights.service[0].reviews)}). It is not evidence of product quality.
				{:else}
					Delivery praise is shown separately from product quality.
				{/if}
			</p>
			<p class="mt-1 text-xs text-muted-foreground">Counts refer to distinct reviews mentioning each quality. Positive feedback does not cancel any safety or defect reports.</p>
		</section>
	</div>
{/key}
