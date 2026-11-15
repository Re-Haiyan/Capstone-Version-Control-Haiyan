<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import CircleHelpIcon from '@lucide/svelte/icons/circle-help';
	import InfoIcon from '@lucide/svelte/icons/info';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { chipFor, view } from '#lib/product.js';
	import type { ConclusionDecision, Product, WhyItem } from '#lib/types.js';
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
	// Safety and authenticity reports come on their own (`warnings`) and are shown in the open, set apart from the paragraph.
	// `body` is the paragraph without them; a report saved without them shows `summary` as before.
	const warnings = $derived(conclusion?.warnings ?? []);
	const paragraph = $derived((warnings.length ? conclusion?.body : conclusion?.summary) || conclusion?.text || verdict.detail);

	// "Why this conclusion?": every line is a count of distinct reviews, with the reviewers' own words behind it.
	// The server sends it only when the saved report kept its review text; otherwise this section is simply absent.
	const why = $derived(conclusion?.evidence?.why ?? []);
	const GROUPS: { kind: WhyItem['kind']; title: string }[] = [
		{ kind: 'product', title: 'About the product' },
		{ kind: 'trust', title: 'Authenticity, as reviewers describe it' },
		{ kind: 'service', title: 'Delivery and seller (not about the product itself)' }
	];
	const groups = $derived(GROUPS.map((group) => ({ ...group, items: why.filter((item) => item.kind === group.kind).slice(0, 8) })).filter((group) => group.items.length));
	const LANGUAGE = { en: 'English', fil: 'Filipino', taglish: 'Taglish' } as const;
	const reviewWord = (count: number) => (count === 1 ? '1 review' : `${count} reviews`);
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
			{#each warnings as warning (warning)}
				<p class="verdict-step bg-background/70 text-foreground flex items-start gap-2 rounded-lg border-l-4 border-(--tone) px-3 py-2 text-sm font-medium" role="note" style="--d: 0.46s">
					<TriangleAlertIcon class="mt-0.5 size-4 shrink-0 text-(--tone)" aria-hidden="true" />
					<span>{warning}</span>
				</p>
			{/each}
			{#if conclusion}
				<!-- The verdict itself, as the checker words it. -->
				<p class="verdict-step text-foreground/80 text-sm" style="--d: 0.5s"><b class="text-foreground font-medium">{verdict.headline}.</b> {verdict.detail}</p>
			{/if}
			{#if groups.length}
				<details class="verdict-step group/why border-(--tone)/30 border-t pt-3" style="--d: 0.54s">
					<summary class="text-foreground flex min-h-11 cursor-pointer list-none items-center gap-1.5 text-sm font-medium [&::-webkit-details-marker]:hidden">
						<ChevronDownIcon class="size-4 transition-transform group-open/why:rotate-180" aria-hidden="true" />
						Why this conclusion?
					</summary>
					<div class="grid gap-4 pt-2">
						{#each groups as group (group.kind)}
							<section class="grid gap-2">
								<h3 class="text-muted-foreground text-xs font-medium tracking-wide uppercase">{group.title}</h3>
								<ul class="grid gap-2">
									{#each group.items as item (item.aspect + item.polarity)}
										<li class="grid gap-1 text-sm">
											<span class="flex flex-wrap items-baseline gap-x-2">
												<span class={cn('text-foreground rounded-full border px-2 py-0.5 text-xs font-medium', item.polarity === 'positive' ? 'border-emerald-600/70' : 'border-amber-600/80')}>{item.polarity === 'positive' ? 'Praised' : 'Concern'}</span>
												<span class="text-foreground">{item.text}</span>
											</span>
											{#if item.quotes.length}
												<details class="text-muted-foreground">
													<summary class="min-h-8 cursor-pointer text-xs underline-offset-2 hover:underline">Read {item.quotes.length === item.reviews ? (item.reviews === 1 ? 'the review' : `all ${item.reviews} reviews`) : `${item.quotes.length} of ${item.reviews} reviews`}</summary>
													<ul class="grid gap-1.5 pt-1">
														{#each item.quotes as quote (quote.review_id)}
															<li class="border-(--tone)/30 border-l-2 pl-2 text-sm">
																<q lang={quote.language === 'en' ? 'en' : 'fil'} class="text-foreground/90">{quote.text}</q>
																<span class="text-muted-foreground block text-xs">{quote.rating ? `${quote.rating} of 5 stars · ` : ''}{LANGUAGE[quote.language]}</span>
															</li>
														{/each}
													</ul>
												</details>
											{/if}
										</li>
									{/each}
								</ul>
							</section>
						{/each}
						<p class="text-muted-foreground text-xs">
							Counts are distinct reviews among the {conclusion?.evidence?.reviews_considered} analyzed. Each review counts once per feature; copied reviews, tag blocks picked from a menu, reviews that have not used the product yet, and comparisons are left out.
						</p>
					</div>
				</details>
			{/if}
			<p class="verdict-step text-muted-foreground text-sm" style="--d: 0.56s">Based on customer reviews, not independent product verification. Review signals are a guide, not proof.</p>
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
