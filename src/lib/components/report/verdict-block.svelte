<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import InfoIcon from '@lucide/svelte/icons/info';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import type { ConclusionDecision, Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	// One card for the verdict and the conclusion. It says what reviewers REPORT, never that a product is safe or
	// unsafe. The server words the lead sentence, the paragraph that counts the reviews behind each concern, and the
	// assessment; the verdict (the safety wording shoppers are told to read) stays underneath, unchanged.
	// It arrives in steps: the box settles in and takes its colour, then the icon, the headline and the detail follow.
	let { product }: { product: Product } = $props();

	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const conclusion = $derived(verdict.conclusion);

	// The assessment takes the conclusion's own colour, from the same four as the verdict.
	const TONE: Record<ConclusionDecision, 'clear' | 'caution' | 'safety' | 'unknown'> = {
		recommended: 'clear',
		mixed: 'caution',
		caution: 'caution',
		not_recommended: 'safety',
		not_enough: 'unknown'
	};
	const assessTone = $derived(conclusion ? TONE[conclusion.decision] : chip.kind);
	const lead = $derived(conclusion?.lead || conclusion?.headline || verdict.headline);
	const paragraph = $derived(conclusion?.summary || conclusion?.text || verdict.detail);
</script>

<!-- Keyed on the product, so opening another report plays the reveal again. -->
{#key product.link}
	<div class={cn('verdict-box tone-' + chip.kind, 'text-foreground grid min-w-0 gap-4 rounded-xl border-2 border-(--tone)/60 bg-(--tone-soft) p-4 [overflow-wrap:anywhere] sm:p-5 md:grid-cols-[minmax(0,1fr)_auto] md:gap-6 md:p-6')} role="group" aria-label="Result">
		<div class="grid min-w-0 content-start gap-3">
			<div class="verdict-step flex flex-wrap items-center gap-2 text-sm font-medium" style="--d: 0.2s">
				<span class="relative grid size-5 place-items-center">
					{#if chip.kind === 'safety'}
						<span class="verdict-ring absolute inset-0 rounded-full bg-(--tone)/30" aria-hidden="true"></span>
					{/if}
					<span class="pop relative text-(--tone)" style="animation-delay: 0.2s">
						{#if chip.kind === 'safety'}<TriangleAlertIcon class="size-5" />
						{:else if chip.kind === 'caution'}<CircleAlertIcon class="size-5" />
						{:else if chip.kind === 'clear'}<CircleCheckIcon class="size-5" />
						{:else}<CircleHelpIcon class="size-5" />{/if}
					</span>
				</span>
				<span>Product Conclusion</span>
				<span class="sr-only">{chip.label}</span>
				<!-- On a phone this would drop onto a line of its own; there the headline and the "guide, not proof" line say it. -->
				<span class="text-muted-foreground font-normal max-sm:sr-only">· What reviewers report</span>
			</div>
			<h2 class="verdict-step text-foreground text-2xl leading-tight font-semibold tracking-tight md:text-3xl" style="--d: 0.32s">{lead}</h2>
			{#if paragraph}<p class="verdict-step text-foreground/80 text-base" style="--d: 0.44s">{paragraph}</p>{/if}
			{#if conclusion}
				<!-- The verdict itself, as the checker words it. -->
				<p class="verdict-step text-foreground/80 text-sm" style="--d: 0.5s"><b class="text-foreground font-medium">{verdict.headline}.</b> {verdict.detail}</p>
			{/if}
			<p class="verdict-step text-muted-foreground text-sm" style="--d: 0.56s">Review signals are a guide, not proof.</p>
		</div>
		{#if conclusion?.assessment}
			<div class="verdict-step grid content-center justify-items-start gap-3 md:justify-items-center md:border-l md:border-(--tone)/30 md:pl-6" style="--d: 0.5s">
				<div class={cn('tone-' + assessTone, 'grid gap-0.5 rounded-xl border border-(--tone)/60 bg-(--tone-soft) px-4 py-2.5 md:min-w-44')}>
					<span class="text-foreground flex items-center gap-1.5 text-sm font-medium">
						{#if assessTone === 'safety'}<TriangleAlertIcon class="size-4 text-(--tone)" />
						{:else if assessTone === 'caution'}<CircleAlertIcon class="size-4 text-(--tone)" />
						{:else if assessTone === 'clear'}<CircleCheckIcon class="size-4 text-(--tone)" />
						{:else}<CircleHelpIcon class="size-4 text-(--tone)" />{/if}
						Overall assessment
					</span>
					<span class="text-foreground text-2xl leading-tight font-semibold tracking-tight">{conclusion.assessment}</span>
				</div>
				{#if conclusion.assessment_note}
					<p class="text-foreground/80 flex max-w-52 items-start gap-1.5 text-sm md:text-left">
						<InfoIcon class="text-muted-foreground mt-0.5 size-4 shrink-0" aria-hidden="true" />
						<span>{conclusion.assessment_note}</span>
					</p>
				{/if}
			</div>
		{/if}
	</div>
{/key}
