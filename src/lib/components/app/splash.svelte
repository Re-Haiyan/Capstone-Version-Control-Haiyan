<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import logo from '#lib/assets/logo.png';

	// The backdrop: a collage of product photos, like the items people check on shopping sites.
	const photos = Object.values(import.meta.glob('#lib/assets/products/*.webp', { eager: true, import: 'default', query: '?url' })) as string[];
	// Split into columns that scroll down at different speeds, like scrolling a shopping feed.
	// Stepping by 7 mixes the gadgets (added last) in among the other items.
	const mixed = photos.map((_, i) => photos[(i * 7) % photos.length]);
	const columns = Array.from({ length: 8 }, (_, c) => mixed.filter((_, i) => i % 8 === c));

	// The screen people see first: the logo, the name and the tagline over the product collage. Explore leads to the
	// sign-in page (/enter). It stays until the person presses Explore,
	// and is not shown again in that browser tab after that (a reload or a new page does not play it again).
	let show = $state(false);
	let leaving = $state(false);

	function enter() {
		if (leaving) return;
		leaving = true;
		try {
			sessionStorage.setItem('splash-seen', '1');
		} catch {
			// Storage can be blocked; the screen then simply shows again next time.
		}
		setTimeout(() => (show = false), 500);
		void goto('/enter');
	}

	onMount(() => {
		try {
			if (sessionStorage.getItem('splash-seen')) return;
		} catch {
			// Storage blocked: show the screen.
		}
		show = true;
	});
</script>

<svelte:window onkeydown={(e) => show && e.key === 'Enter' && enter()} />

{#if show}
	<div class="splash" class:leaving role="dialog" aria-label="DeFaketive. A safer you.">
		<div class="collage" aria-hidden="true">
			{#each columns as col, c (c)}
				<div class="col" style:--dur="{34 + (c % 4) * 9}s" style:--off="{-((c * 37) % 100) / 100}">
					<div class="track">
						{#each [...col, ...col] as src, i (i)}
							<div class="tile"><img {src} alt="" /></div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
		<span class="swoosh tl" aria-hidden="true"></span>
		<span class="swoosh br" aria-hidden="true"></span>
		<div class="stack">
			<img src={logo} alt="" class="mark" />
			<div class="name" aria-hidden="true"><span>De</span><span class="f">F</span><span>aketive</span></div>
			<div class="tag"><i></i><span>A SAFER YOU</span><i></i></div>
			<button type="button" class="go" onclick={enter} aria-label="Explore">
				<span>Explore</span>
				<ArrowRightIcon class="go-arrow" size={21} strokeWidth={2.5} aria-hidden="true" />
			</button>
		</div>
	</div>
{/if}

<style>
	.splash {
		--navy: #0b1f4d;
		--mustard: #f5b014;
		position: fixed;
		inset: 0;
		z-index: 200;
		display: grid;
		place-items: center;
		overflow: hidden;
		background: #0b1f4d;
		color: var(--navy);
		transition: opacity 0.5s ease, transform 0.5s ease;
	}
	.splash.leaving {
		opacity: 0;
		transform: scale(1.04);
		pointer-events: none;
	}
	.collage {
		position: absolute;
		inset: -4%;
		display: grid;
		grid-template-columns: repeat(8, minmax(9rem, 1fr));
		gap: 0.9rem;
		padding: 0 0.5rem;
		transform: rotate(-4deg) scale(1.12);
	}
	/* Brand wash over the collage: navy at the edges, clearing in the middle where the logo sits. */
	.collage::after {
		content: '';
		position: absolute;
		inset: 0;
		background: radial-gradient(ellipse at 50% 50%, rgba(250, 249, 247, 0.3) 0%, rgba(11, 31, 77, 0.28) 70%, rgba(11, 31, 77, 0.55) 100%);
	}
	.col {
		overflow: hidden;
		min-width: 0;
	}
	.track {
		display: grid;
		gap: 0.9rem;
		/* Two identical halves: moving by half a track and looping is seamless. */
		animation: feed var(--dur) linear infinite;
		animation-delay: calc(var(--dur) * var(--off));
	}
	.tile {
		aspect-ratio: 1;
		overflow: hidden;
		border-radius: 1.1rem;
		/* The warm off-white of the app's own pages, with a thin mustard edge. */
		background: #faf9f7;
		box-shadow: 0 0 0 2px rgba(245, 176, 20, 0.55), 0 10px 22px -10px rgba(5, 14, 40, 0.7);
	}
	.tile img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		padding: 0.4rem;
	}
	@keyframes feed {
		from {
			transform: translateY(-50%);
		}
		to {
			transform: translateY(0);
		}
	}
	.stack {
		position: relative;
		z-index: 1;
		padding: clamp(1rem, 3vw, 2rem) !important;
		display: grid;
		justify-items: center;
		gap: 0.8rem;
		padding: 1.5rem;
		text-align: center;
	}
	.stack::before {
		content: '';
		position: absolute;
		z-index: -1;
		inset: -34% -46%;
		pointer-events: none;
		background: radial-gradient(closest-side, rgba(255, 255, 255, 0.86) 0%, rgba(255, 255, 255, 0.62) 45%, rgba(255, 255, 255, 0) 100%);
	}
	.mark {
		width: clamp(4.5rem, 12vw, 6.5rem);
		filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.9)) drop-shadow(0 0 22px rgba(255, 255, 255, 0.6));
		animation: pop 0.9s cubic-bezier(0.2, 0.9, 0.3, 1.25) 0.15s both;
	}
	.name {
		font: 900 clamp(1.8rem, 5.5vw, 3.2rem) / 1 'Archivo Black', 'Arial Black', Impact, sans-serif;
		text-shadow: 0 0 10px rgba(255, 255, 255, 0.95), 0 0 24px rgba(255, 255, 255, 0.7), 0 0 2px #fff;
		font-style: italic;
		letter-spacing: -0.02em;
		animation: up 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) 0.7s both;
	}
	.f {
		color: var(--mustard);
	}
	.tag {
		display: flex;
		align-items: center;
		gap: 1rem;
		font: 600 clamp(0.65rem, 1.8vw, 0.85rem) / 1 Inter, system-ui, sans-serif;
		letter-spacing: 0.45em;
		font-weight: 800;
		text-shadow: 0 0 8px #fff, 0 0 18px rgba(255, 255, 255, 0.85);
		animation: up 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) 1.1s both;
	}
	.tag i {
		display: block;
		width: clamp(1.5rem, 6vw, 3.5rem);
		height: 2px;
		box-shadow: 0 0 8px rgba(255, 255, 255, 0.95);
		border-radius: 2px;
		background: var(--navy);
		transform-origin: center;
		animation: grow 0.7s ease-out 1.4s both;
	}
	/* One obvious first action: large enough for touch, gold against the navy
	   collage, with a light separation ring so the product photos don't compete. */
	.go {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		margin-top: 1.1rem;
		min-height: 3.75rem;
		min-width: 15rem;
		max-width: calc(100vw - 2.5rem);
		padding: 0.85rem 1.65rem;
		border: 2px solid var(--navy);
		border-radius: 999px;
		background: linear-gradient(180deg, #ffd15f 0%, var(--mustard) 60%, #ed9f05 100%);
		color: var(--navy);
		font: 800 clamp(1.1rem, 1.6vw, 1.3rem) / 1.2 Inter, system-ui, sans-serif;
		letter-spacing: 0.01em;
		white-space: nowrap;
		box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.82), 0 0 26px rgba(245, 176, 20, 0.42), 0 14px 28px -7px rgba(5, 14, 40, 0.75);
		cursor: pointer;
		transition: background-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
		animation: up 0.65s ease-out 0.85s both;
	}
	.go:hover {
		background: linear-gradient(180deg, #ffe08b 0%, #ffc444 100%);
		box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.92), 0 18px 32px -7px rgba(5, 14, 40, 0.8);
		transform: translateY(-2px);
	}
	.go:active {
		transform: translateY(1px);
	}
	.go:focus-visible {
		outline: 4px solid #315ec9;
		outline-offset: 7px;
	}
	.go-arrow {
		flex: none;
		transition: transform 180ms ease;
	}
	.go:hover .go-arrow {
		transform: translateX(3px);
	}
	@media (max-width: 480px) {
		.go {
			width: min(19rem, 83vw);
		}
	}
	.swoosh {
		position: absolute;
		width: 70vmax;
		height: 70vmax;
		border-radius: 50%;
		/* Lit from the visible corner, with a fine ring pattern, so the navy is not a flat block. */
		background: repeating-radial-gradient(circle at 50% 50%, transparent 0 2.2vmax, rgba(255, 255, 255, 0.045) 2.2vmax 2.35vmax), radial-gradient(circle at 78% 78%, #1d3f94 0%, #12306f 28%, var(--navy) 62%, #081638 100%);
		box-shadow: 0 0 0 0.9vmax var(--mustard), 0 0 3vmax rgba(5, 14, 40, 0.55);
	}
	/* Two thin arcs echoing the mustard edge, set in from it. */
	.swoosh::before,
	.swoosh::after {
		content: '';
		position: absolute;
		border-radius: 50%;
	}
	.swoosh::before {
		inset: 2.4vmax;
		border: 2px solid rgba(245, 176, 20, 0.6);
	}
	.swoosh::after {
		inset: 4.6vmax;
		border: 1px solid rgba(255, 255, 255, 0.22);
	}
	.tl {
		left: -52vmax;
		top: -52vmax;
		animation: slide-tl 1.1s cubic-bezier(0.2, 0.7, 0.2, 1) both;
	}
	.br {
		right: -52vmax;
		bottom: -52vmax;
		animation: slide-br 1.1s cubic-bezier(0.2, 0.7, 0.2, 1) 0.15s both;
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: scale(0.3) rotate(-12deg);
		}
	}
	@keyframes up {
		from {
			opacity: 0;
			transform: translateY(26px);
		}
	}
	@keyframes grow {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes slide-tl {
		from {
			transform: translate(-30vmax, -30vmax);
		}
	}
	@keyframes slide-br {
		from {
			transform: translate(30vmax, 30vmax);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.mark,
		.name,
		.tag,
		.tag i,
		.go,
		.track,
		.swoosh {
			animation: none;
		}
		.splash {
			transition: opacity 0.2s;
		}
		.go,
		.go-arrow {
			transition: none;
		}
	}
</style>
