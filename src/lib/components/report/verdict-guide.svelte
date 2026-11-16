<script lang="ts">
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import { accuracyBrief, chipFor, VERDICT_GROUPS, view } from '#lib/product.js';
	import type { Product } from '#lib/types.js';
	import { cn } from '#lib/utils.js';

	let { product }: { product: Product } = $props();
	const verdict = $derived(view(product));
	const chip = $derived(chipFor(product));
	const current = $derived(VERDICT_GROUPS.find((group) => group.kind === chip.kind));
	const others = $derived(VERDICT_GROUPS.filter((group) => group.kind !== chip.kind));
</script>

<Card id="report-guide" tabindex={-1} aria-labelledby="guide-heading" class="min-w-0 scroll-mt-20 gap-4 [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-ring">
	<CardHeader class="gap-1.5">
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">How the checker works</p>
		<CardTitle><h2 id="guide-heading" class="text-lg font-semibold">What this result means</h2></CardTitle>
		<CardDescription>Based on patterns in customer reviews, not a product safety certification.</CardDescription>
	</CardHeader>
	<CardContent class="grid gap-3">
		{#if current}
			<div class={cn('tone-' + current.kind, 'grid gap-1 rounded-lg border border-(--tone)/50 bg-(--tone-soft) p-3')}>
				<p class="flex items-center gap-2 text-sm font-semibold">
					<i class="size-2.5 shrink-0 rounded-full bg-(--tone)" aria-hidden="true"></i>
					{current.label}
					<Badge variant="secondary">This product</Badge>
				</p>
				<p class="text-sm">{current.meaning}</p>
			</div>
		{/if}
		<details class="group/labels rounded-lg border px-3 py-2">
			<summary class="flex min-h-7 cursor-pointer items-center gap-2 text-sm font-medium [&::-webkit-details-marker]:hidden">
				<ChevronDownIcon class="size-4 transition-transform group-open/labels:rotate-180" aria-hidden="true" />
				Other result labels explained
			</summary>
			<ul class="grid gap-3 border-t pt-3">
				{#each others as group (group.kind)}
					<li class="grid gap-0.5">
						<span class="flex items-center gap-2 text-sm font-semibold">
							<i class="tone-{group.kind} size-2.5 shrink-0 rounded-full bg-(--tone)" aria-hidden="true"></i>
							{group.label}
						</span>
						<p class="text-muted-foreground text-xs">{group.meaning}</p>
					</li>
				{/each}
			</ul>
		</details>
		<p class="text-muted-foreground text-xs">{accuracyBrief(verdict.safety_check_accuracy)}</p>
	</CardContent>
</Card>
