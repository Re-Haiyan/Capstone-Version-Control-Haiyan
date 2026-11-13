<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { view } from '#lib/product.js';
	import type { ConclusionDecision, Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	// What the reviews add up to: "Based on the reviews of this product ...". The server words it and picks the
	// decision from the verdict and the reviewers' mood. It reports what reviewers say, it does not promise anything.
	let { product }: { product: Product } = $props();

	const conclusion = $derived(view(product).conclusion);

	// The same four colours as the verdict, so the two boxes never disagree in tone.
	const TONE: Record<ConclusionDecision, 'clear' | 'caution' | 'safety' | 'unknown'> = {
		recommended: 'clear',
		mixed: 'caution',
		caution: 'caution',
		not_recommended: 'safety',
		not_enough: 'unknown'
	};
	const tone = $derived(conclusion ? TONE[conclusion.decision] : 'unknown');
</script>

{#if conclusion}
	<section class={cn('tone-' + tone, 'text-foreground grid gap-2 rounded-xl border border-(--tone)/60 bg-(--tone-soft) p-4 md:p-5')} aria-labelledby="conclusion-heading">
		<div class="flex items-center gap-2 text-sm font-medium">
			<span class="text-(--tone)">
				{#if tone === 'safety'}<TriangleAlertIcon class="size-5" />
				{:else if tone === 'caution'}<CircleAlertIcon class="size-5" />
				{:else if tone === 'clear'}<CircleCheckIcon class="size-5" />
				{:else}<CircleHelpIcon class="size-5" />{/if}
			</span>
			<span>Conclusion from the reviews</span>
		</div>
		<h3 id="conclusion-heading" class="text-foreground text-xl leading-tight font-semibold tracking-tight md:text-2xl">{conclusion.headline}</h3>
		<p class="text-foreground/80 text-base">{conclusion.text}</p>
		{#if conclusion.points.length}
			<ul class="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-sm">
				{#each conclusion.points as point, index (index)}<li>{point}</li>{/each}
			</ul>
		{/if}
		<p class="text-muted-foreground text-sm">{conclusion.notice}</p>
	</section>
{/if}
