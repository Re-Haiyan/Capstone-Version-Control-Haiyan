<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import { Button } from '#lib/components/ui/button/index.js';

	let {
		words,
		active,
		onpick
	}: {
		words: { word: string; category: string; count: number }[];
		active: string;
		onpick: (word: string) => void;
	} = $props();

	const top = $derived(words.slice(0, 6));
	const max = $derived(top[0]?.count || 1);
</script>

<Card class="min-w-0 [overflow-wrap:anywhere]">
	<CardHeader>
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Warning words</p>
		<CardTitle><h2 class="text-xl font-semibold">Warning words found</h2></CardTitle>
		<CardDescription>Words the check matched in these reviews. Pick one to see its reviews.</CardDescription>
	</CardHeader>
	<CardContent class="grid grid-cols-[minmax(0,1fr)_minmax(2rem,1fr)_auto] items-center gap-x-3 gap-y-3">
		<!-- Flexible columns keep long words and the count inside narrow cards. -->
		{#each top as item (item.word)}
			<Button
				variant={active === item.word ? 'secondary' : 'outline'}
				size="sm"
				class="h-auto min-h-11 min-w-0 max-w-full justify-self-start py-2 text-left whitespace-normal"
				aria-pressed={active === item.word}
				aria-label="{active === item.word ? 'Clear filter for' : 'Show reviews mentioning'} {item.word}"
				title="Show reviews that mention this"
				onclick={() => onpick(item.word)}>{item.word}</Button
			>
			<!-- A count of reviews: plain, never the brand colour. -->
			<Progress value={(item.count / max) * 100} aria-label="{item.count} reviews" class="[&>div]:bg-foreground" />
			<b class="text-sm tabular-nums">{item.count}×</b>
		{:else}
			<p class="text-muted-foreground col-span-3 text-sm">The check matched no warning words in these reviews.</p>
		{/each}
	</CardContent>
</Card>
