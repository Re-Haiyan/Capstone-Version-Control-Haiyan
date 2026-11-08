<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import { Alert, AlertDescription, AlertTitle } from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { scan } from '#lib/stores/scan.svelte.js';
</script>

{#if scan.feedback}
	<Alert
		variant={scan.feedback.kind === 'error' ? 'destructive' : 'default'}
		class={scan.feedback.kind === 'warning' ? 'tone-caution border-(--tone)/50 bg-(--tone-soft) *:[svg]:text-(--tone)' : ''}
	>
		<CircleAlertIcon aria-hidden="true" />
		<AlertTitle>{scan.feedback.title}</AlertTitle>
		<AlertDescription>{scan.feedback.message}</AlertDescription>
		{#if scan.summary?.state === 'attention' && scan.summary.id}
			<div class="col-start-2 mt-3">
				<Button type="button" variant="outline" onclick={() => scan.reconnect()}>Reconnect to scan</Button>
			</div>
		{/if}
	</Alert>
{/if}
