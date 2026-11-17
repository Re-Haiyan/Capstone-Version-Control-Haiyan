<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import ThumbsUpIcon from '@lucide/svelte/icons/thumbs-up';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import { positiveHighlights } from '#lib/positive-highlights.js';
	import type { Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	let { product }: { product: Product } = $props();

	const chip = $derived(chipFor(product));
	const verdict = $derived(view(product));
	const heading = $derived(chip.label);
	const analyzed = $derived(Math.max(0, Number(verdict.reviews_analyzed) || 0));

	// Include every review-backed product quality, rather than only the top three.
	// Seller / delivery compliments are not product-quality evidence.
	const highlights = $derived(positiveHighlights(verdict.conclusion, Infinity));

	type ConcernBadge = { category: string; label: string; reviews: number };
	const fallbackLabels: Record<string, string> = {
		safety: 'Possible safety concern',
		defect: 'Faults or failures',
		quality: 'Quality concerns',
		counterfeit: 'Possible authenticity issue',
		not_as_described: 'Different from listing'
	};

	// A saved report may have counts without expanded badges. Merge both sources
	// and keep one entry per category, without adding overlapping review counts.
	const concerns = $derived.by((): ConcernBadge[] => {
		const byCategory = new Map<string, ConcernBadge>();
		for (const [category, raw] of Object.entries(verdict.counts ?? {})) {
			const reviews = Number(raw);
			if (!Number.isSafeInteger(reviews) || reviews <= 0) continue;
			byCategory.set(category, {
				category,
				label: fallbackLabels[category] ?? category.replaceAll('_', ' '),
				reviews
			});
		}
		for (const badge of verdict.badges ?? []) {
			const reviews = Number(badge.mentions);
			if (!Number.isSafeInteger(reviews) || reviews <= 0) continue;
			const old = byCategory.get(badge.category);
			byCategory.set(badge.category, {
				category: badge.category,
				label: badge.label || old?.label || fallbackLabels[badge.category] || badge.category,
				reviews: Math.max(old?.reviews ?? 0, reviews)
			});
		}
		return [...byCategory.values()].sort((a, b) => b.reviews - a.reviews || a.label.localeCompare(b.label));
	});

	const headline = $derived(
		chip.kind === 'safety'
			? 'A possible safety concern was reported.'
			: chip.kind === 'caution'
				? 'Some product concerns were reported.'
				: chip.kind === 'clear'
					? 'No warning-level concerns were detected.'
					: 'There is not enough evidence for a clear result.'
	);
	const nextStep = $derived(
		chip.kind === 'safety'
			? 'Reported concerns are unverified. Read the flagged reviews carefully before deciding to buy.'
			: chip.kind === 'caution'
				? 'Compare the flagged reviews with the product listing before deciding to buy.'
				: chip.kind === 'clear'
					? 'This does not guarantee the product is safe, authentic, or reliable.'
					: 'Examine the available reviews, product details, and seller information before buying.'
	);
</script>

{#key product.link}
	<div class="grid min-w-0 gap-3">
		<section
			class={cn(
				'verdict-box tone-' + chip.kind,
				'min-w-0 rounded-xl border border-(--tone)/60 bg-(--tone-soft) p-4 text-foreground shadow-xs [overflow-wrap:anywhere] sm:p-5'
			)}
			role="group"
			aria-label="Product review result"
		>
			<div class="flex flex-wrap items-center justify-between gap-2">
				<h2 class="flex items-center gap-2 text-sm font-semibold">
					{#if chip.kind === 'safety'}
						<TriangleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
					{:else if chip.kind === 'caution'}
						<CircleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
					{:else if chip.kind === 'clear'}
						<CircleCheckIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
					{:else}
						<CircleHelpIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
					{/if}
					Review Summary
				</h2>
				<span class="rounded-full border border-(--tone)/35 bg-background/75 px-2.5 py-1 text-xs font-medium text-foreground">{heading}</span>
			</div>
			<p class="mt-2 text-lg font-semibold leading-snug tracking-tight sm:text-xl">{headline}</p>
			<p class="mt-2 text-sm leading-relaxed text-foreground/85">
				{#if analyzed > 0}
					We analyzed {analyzed.toLocaleString()} review{analyzed === 1 ? '' : 's'}.
				{/if}
				{nextStep}
			</p>
		</section>

		<div class="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2" aria-label="Review highlights">
			<section class="min-w-0 rounded-xl border border-emerald-600/20 bg-emerald-500/5 p-4 dark:bg-emerald-950/20" aria-labelledby="positive-highlights-title">
				<h3 id="positive-highlights-title" class="mb-3 flex items-center gap-2 text-sm font-semibold">
					<ThumbsUpIcon class="size-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden="true" />
					What reviewers liked
				</h3>
				{#if highlights.product.length}
					<ul class="flex min-w-0 list-none flex-wrap gap-2 p-0">
						{#each highlights.product as item (item.key)}
							<li class="max-w-full rounded-full border border-emerald-600/25 bg-background/75 px-3 py-1.5 text-xs leading-snug sm:text-sm">
								<span class="break-words font-medium">{item.label}</span>
								<span class="ml-1 whitespace-nowrap text-muted-foreground">({item.reviews})</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-muted-foreground text-sm">
						{highlights.available ? 'No clear positive product qualities were identified.' : 'Product praise details are not available for this report.'}
					</p>
				{/if}
			</section>

			<section class="min-w-0 rounded-xl border border-amber-600/25 bg-amber-500/5 p-4 dark:bg-amber-950/20" aria-labelledby="reported-concerns-title">
				<h3 id="reported-concerns-title" class="mb-3 flex items-center gap-2 text-sm font-semibold">
					<TriangleAlertIcon class="size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
					Common concerns
				</h3>
				{#if concerns.length}
					<ul class="flex min-w-0 list-none flex-wrap gap-2 p-0">
						{#each concerns as item (item.category)}
							<li class="max-w-full rounded-full border border-amber-600/30 bg-background/75 px-3 py-1.5 text-xs leading-snug sm:text-sm">
								<span class="break-words font-medium">{item.label}</span>
								<span class="ml-1 whitespace-nowrap text-muted-foreground">({item.reviews})</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-muted-foreground text-sm">
						{verdict.available ? 'No specific issue categories were identified in this sample.' : 'Concern details are not available for this report.'}
					</p>
				{/if}
			</section>
		</div>

		{#if highlights.product.length || concerns.length}
			<p class="text-muted-foreground text-xs leading-relaxed">
				Numbers show reviews mentioning each topic. A single review may appear under more than one badge; counts should not be added together.
				{#if highlights.service.length} Delivery or seller praise is excluded from product-quality badges.{/if}
			</p>
		{/if}

		<div class="rounded-lg border border-border/70 bg-muted/25 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground" aria-label="DeFaketive disclaimer">
			<p><strong class="font-semibold text-foreground/80">Disclaimer:</strong>
			DeFaketive is not 100% accurate and may occasionally produce incorrect classifications, overlook genuine product concerns, or flag reviews that do not indicate an actual problem. The system analyzes customer reviews to provide advisory information and does not guarantee a product's authenticity, quality, or safety. Users are encouraged to examine the supporting reviews, product details, and seller information before making a purchase. The final decision to purchase or avoid a product remains the responsibility of the user.</p>
		</div>
	</div>
{/key}
