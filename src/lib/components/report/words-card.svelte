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

<Card>
	<CardHeader>
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Warning words</p>
		<CardTitle class="text-xl">Warning words found</CardTitle>
		<CardDescription>Words the check matched in these reviews. Pick one to see its reviews.</CardDescription>
	</CardHeader>
	<CardContent class="grid grid-cols-[fit-content(55%)_minmax(4rem,1fr)_auto] items-center gap-x-3 gap-y-3">
		<!-- One grid, so the bars start at the same place. The first column is as wide as the longest word (at most
				 55% of the card); each word's own button is only as wide as that word. -->
		{#each top as item (item.word)}
			<Button
				variant={active === item.word ? 'secondary' : 'outline'}
				size="sm"
				class="h-auto min-h-8 justify-self-start py-1 text-left whitespace-normal"
				aria-pressed={active === item.word}
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
