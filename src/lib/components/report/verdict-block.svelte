<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import { reviewGuidance } from '#lib/review-guidance.js';
	import type { Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	// Restore the former full-width, tone-coded verdict. Add only a short
	// source-grounded buyer-context sentence; no positive-keyword split panels
	// or fabricated "safe to buy" conclusion.
	let { product }: { product: Product } = $props();
	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const guidance = $derived(reviewGuidance(product));
	const heading = $derived(chip.label);
</script>

{#key product.link}
	<div class="grid min-w-0 gap-2.5">
		<section
			class={cn('verdict-box tone-' + chip.kind,
				'min-w-0 overflow-hidden rounded-xl border-2 border-(--tone)/60 bg-(--tone-soft) p-4 text-foreground shadow-xs [overflow-wrap:anywhere] sm:p-5')}
			role="group"
			aria-label="Product review result"
		>
			<div class="flex flex-wrap items-center gap-2 text-sm font-medium">
				{#if chip.kind === 'safety'}
					<TriangleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else if chip.kind === 'caution'}
					<CircleAlertIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else if chip.kind === 'clear'}
					<CircleCheckIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{:else}
					<CircleHelpIcon class="size-4 shrink-0 text-(--tone)" aria-hidden="true" />
				{/if}
				<span>{heading}</span>
				<span class="text-muted-foreground font-normal">· What reviewers report</span>
			</div>

			<h2 class="mt-2 text-xl font-semibold leading-tight tracking-tight sm:text-2xl">{verdict.headline}</h2>
			{#if verdict.detail}
				<p class="mt-2 text-sm leading-relaxed text-foreground/85">{verdict.detail}</p>
			{/if}

			<div class="mt-3 rounded-lg border border-(--tone)/25 bg-background/65 px-3 py-2.5">
				<h3 class="text-xs font-semibold">Quick review summary</h3>
				<p class="mt-1 text-sm leading-relaxed">{guidance.text}</p>
			</div>
			<p class="mt-2 text-xs text-muted-foreground">Review signals are a guide, not proof.</p>
		</section>

		<div class="rounded-lg border border-border/70 bg-muted/25 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground" aria-label="DeFaketive disclaimer">
			<p><strong class="font-semibold text-foreground/80">Disclaimer:</strong>
			DeFaketive is not 100% accurate and may occasionally produce incorrect classifications, overlook genuine product concerns, or flag reviews that do not indicate an actual problem. The system analyzes customer reviews to provide advisory information and does not guarantee a product's authenticity, quality, or safety. Users are encouraged to examine the supporting reviews, product details, and seller information before making a purchase. The final decision to purchase or avoid a product remains the responsibility of the user.</p>
		</div>
	</div>
{/key}
