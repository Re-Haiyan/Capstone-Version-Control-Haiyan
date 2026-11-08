<script lang="ts">
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import OctagonXIcon from '@lucide/svelte/icons/octagon-x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { needsYouTitle, scan } from '#lib/stores/scan.svelte.js';

	// The header's word on the latest scan. It is only there while there is something to look at: a scan running or
	// waiting for someone, or a finished one whose report (or problem) has not been opened yet. Pressing it does what
	// the Home card's button does. On a phone the words shrink to the time or one word; the full text stays for
	// screen readers.
	type Pill = { kind: 'running' | 'waiting' | 'ready' | 'stopped'; text: string; short: string };
	const pill = $derived.by<Pill | null>(() => {
		const summary = scan.summary;
		if (!summary) return null;
		if (summary.state === 'running' && summary.needs_you) {
			return { kind: 'waiting', text: needsYouTitle(summary), short: summary.needs_team ? 'Waiting' : 'Needs you' };
		}
		if (summary.state === 'running') return { kind: 'running', text: `Scanning… ${scan.elapsed}`, short: scan.elapsed };
		if (summary.state === 'attention') return { kind: 'waiting', text: 'Check progress', short: 'Check' };
		if (summary.seen) return null;
		if (summary.state === 'complete') return { kind: 'ready', text: 'Report ready', short: 'Ready' };
		return { kind: 'stopped', text: 'Scan stopped', short: 'Stopped' };
	});
</script>

{#if pill}
	<Button variant="outline" size="sm" class="rounded-full" title="{pill.text}. Open it" aria-label={pill.kind === 'running' ? 'Scan running. View progress' : `${pill.text}. Open it`} onclick={() => scan.open()}>
		{#if pill.kind === 'running'}<Spinner />
		{:else if pill.kind === 'ready'}<CircleCheckIcon class="pop" />
		{:else if pill.kind === 'stopped'}<OctagonXIcon class="text-destructive" />
		{:else}<TriangleAlertIcon />{/if}
		<span class="tabular-nums sm:hidden" aria-hidden="true">{pill.short}</span>
		<span class="tabular-nums max-sm:sr-only">{pill.text}</span>
	</Button>
{/if}
