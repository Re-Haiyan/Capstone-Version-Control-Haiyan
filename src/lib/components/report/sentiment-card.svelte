<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import { sentimentPercentages } from '#lib/product.js';
	import type { Product } from '#lib/types.js';

	let { product, uniqueCount }: { product: Product; uniqueCount: number } = $props();
	const data = $derived(sentimentPercentages(product));
	const weighted = $derived(Boolean(product.sentiment_summary?.sentiment_shares));
	const share = (label: string) => data.find((item) => item.label === label) ?? { value: 0, percent: 0 };
	const rows = $derived(
		([
			{ key: 'positive', name: 'Positive', note: 'Favourable experience or opinion', color: '[&>div]:bg-emerald-600' },
			{ key: 'uncertain', name: 'Neutral or unclear', note: 'No clear positive or negative opinion', color: '[&>div]:bg-slate-500' },
			{ key: 'negative', name: 'Negative', note: 'Problems or dissatisfaction', color: '[&>div]:bg-amber-600' }
		] as const).map((entry) => {
			const s = share(entry.key[0].toUpperCase() + entry.key.slice(1));
			return { ...entry, count: Number(s.value) || 0, percent: Math.max(0, Math.min(100, Number(s.percent) || 0)) };
		})
	);
	const dominant = $derived([...rows].sort((a, b) => b.percent - a.percent)[0]);
</script>

<Card class="min-w-0 gap-4">
	<CardHeader class="gap-1.5">
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Review sentiment</p>
		<CardTitle class="text-lg">How reviewers feel</CardTitle>
		<CardDescription>
			{#if uniqueCount}
				{dominant?.percent >= 50
					? dominant.name + ' was the largest group among ' + uniqueCount + ' analyzed reviews.'
					: 'Opinions vary across ' + uniqueCount + ' analyzed reviews.'}
			{:else}
				No analyzed reviews to summarise yet.
			{/if}
		</CardDescription>
	</CardHeader>
	<CardContent class="grid gap-3">
		{#each rows as row (row.key)}
			<div class="grid gap-1.5">
				<div class="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
					<span class="font-medium">{row.name}</span>
					<b class="tabular-nums">{row.percent.toFixed(0)}%</b>
				</div>
				<Progress value={row.percent} aria-label="{row.name}: {row.percent.toFixed(0)} percent" class={row.color} />
				<p class="text-muted-foreground text-xs">
					{row.note} · {row.count} of {uniqueCount} reviewed
				</p>
			</div>
		{/each}
		{#if weighted}
			<p class="text-muted-foreground rounded-md bg-muted/50 px-3 py-2 text-xs">
				Percentages are adjusted for the listing's star distribution; the review counts show the actual sample.
			</p>
		{/if}
		<p class="text-muted-foreground text-xs">Sentiment alone does not override safety or authenticity reports.</p>
	</CardContent>
</Card>
