<script lang="ts">
	import { PieChart, Text } from 'layerchart';
	import * as Chart from '#lib/components/ui/chart/index.js';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import CountUp from '#lib/components/app/count-up.svelte';
	import { sentimentPercentages } from '#lib/product.js';
	import type { Product } from '#lib/types.js';

	let { product, uniqueCount }: { product: Product; uniqueCount: number } = $props();

	const data = $derived(sentimentPercentages(product));
	const weighted = $derived(Boolean(product.sentiment_summary?.sentiment_shares));
	const share = (label: string) => data.find((item) => item.label === label) ?? { value: 0, percent: 0 };

	// The verdict colours: teal, grey, orange. Never red, so a negative review can't be mistaken for a safety report.
	// Each slice also has its name and number in the list, so colour is never the only cue.
	const config = {
		positive: { label: 'Positive reviews', color: 'var(--success)' },
		uncertain: { label: 'Mixed or unclear reviews', color: 'var(--unknown)' },
		negative: { label: 'Negative reviews', color: 'var(--warning)' }
	} satisfies Chart.ChartConfig;

	const rows = $derived(
		(['positive', 'uncertain', 'negative'] as const).map((key) => {
			const item = share(key[0].toUpperCase() + key.slice(1));
			return { key, label: config[key].label, color: config[key].color, percent: item.percent, value: item.value };
		})
	);
	const summary = $derived(rows.map((r) => `${r.percent.toFixed(0)}% ${r.key}`).join(', '));
</script>

<Card>
	<CardHeader>
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Sentiment distribution</p>
		<CardTitle class="text-xl">Review sentiment</CardTitle>
		<CardDescription>
			{weighted
				? 'We read extra low-star reviews on purpose, so the percentages are adjusted to reflect the whole listing.'
				: 'How the reviews lean. Shown for context; it does not change the result.'}
		</CardDescription>
	</CardHeader>
	<CardContent class="flex-1 flex-row flex-wrap content-center items-center gap-6">
		<div class="size-40 shrink-0" role="img" aria-label="Sentiment: {summary}">
			<Chart.Container {config} class="aspect-square size-full">
				<PieChart
					data={rows}
					key="key"
					value="percent"
					c="color"
					innerRadius={-14}
					padding={4}
					cornerRadius={3}
					padAngle={0.02}
					props={{ pie: { motion: 'tween' } }}
				>
					{#snippet aboveMarks()}
						<Text value={String(uniqueCount)} textAnchor="middle" verticalAnchor="middle" class="fill-foreground text-xl! font-semibold" dy={-4} />
						<Text value="reviews" textAnchor="middle" verticalAnchor="middle" class="fill-muted-foreground text-xs!" dy={14} />
					{/snippet}
					{#snippet tooltip()}
						<Chart.Tooltip hideLabel />
					{/snippet}
				</PieChart>
			</Chart.Container>
		</div>
		<ul class="grid flex-1 gap-3 text-sm">
			{#each rows as row (row.key)}
				<li class="flex items-center gap-3">
					<i class="size-3 shrink-0 rounded-full border" style="background: {row.color}" aria-hidden="true"></i>
					<span class="flex-1">
						{row.label}
						<small class="text-muted-foreground block text-xs">
							{weighted ? `${row.value} of ${uniqueCount} read` : `${row.percent.toFixed(0)}% of reviews`}
						</small>
					</span>
					<b class="tabular-nums">
						{#if weighted}<CountUp value={row.percent} />%{:else}<CountUp value={row.value} />{/if}
					</b>
				</li>
			{/each}
		</ul>
	</CardContent>
</Card>
