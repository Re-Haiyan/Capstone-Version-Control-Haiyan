<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#lib/components/ui/card/index.js';
	import { Button } from '#lib/components/ui/button/index.js';

	let { words, active, onpick }: {
		words: { word: string; category: string; count: number }[];
		active: string;
		onpick: (word: string) => void;
	} = $props();

	const top = $derived(words.slice(0, 8));
</script>

<Card class="gap-4">
	<CardHeader class="gap-1.5">
		<p class="text-muted-foreground text-xs font-medium tracking-wide uppercase">Flagged review vocabulary</p>
		<CardTitle class="text-lg">Words linked to concerns</CardTitle>
		<CardDescription>Terms the checker matched in review text. Choose a word to read the matching reviews.</CardDescription>
	</CardHeader>
	<CardContent class="grid gap-3">
		{#if top.length}
			<div class="flex flex-wrap gap-2" aria-label="Commonly flagged review terms">
				{#each top as item (item.word)}
					<Button
						variant={active === item.word ? 'secondary' : 'outline'}
						size="sm"
						class="h-auto min-h-9 gap-2 py-1.5 text-left whitespace-normal"
						aria-pressed={active === item.word}
						title="Show reviews mentioning this term"
						onclick={() => onpick(item.word)}
					>
						<span class="break-words">{item.word}</span>
						<b class="text-muted-foreground shrink-0 text-xs tabular-nums">{item.count}</b>
					</Button>
				{/each}
			</div>
			<p class="text-muted-foreground text-xs">Numbers count reviews containing a matched term, not verified incidents. A review may mention more than one term.</p>
		{:else}
			<p class="text-muted-foreground text-sm">No warning terms were matched in the available review text.</p>
		{/if}
	</CardContent>
</Card>
