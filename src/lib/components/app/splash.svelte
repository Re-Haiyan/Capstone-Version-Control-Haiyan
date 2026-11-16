<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import logo from '#lib/assets/logo.png';

	// The backdrop: a collage of product photos, like the items people check on shopping sites.
	const photos = Object.values(import.meta.glob('#lib/assets/products/*.webp', { eager: true, import: 'default', query: '?url' })) as string[];
	// Split into columns that scroll down at different speeds, like scrolling a shopping feed.
	// Stepping by 7 mixes the gadgets (added last) in among the other items.
	const mixed = photos.map((_, i) => photos[(i * 7) % photos.length]);
	const columns = Array.from({ length: 8 }, (_, c) => mixed.filter((_, i) => i % 8 === c));

	// First-time welcome: a readable hero over the existing product collage. Explore leads to
	// the entry page (/enter) with sign-in, sign-up and guest options. The splash stays until Explore,
	// and is not shown again in that browser tab after that (a reload or a new page does not play it again).
	let show = $state(false);
	let leaving = $state(false);
	let exploreButton: HTMLButtonElement | undefined = $state();

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
		// The splash is a modal with only one action. Make that action reachable
		// immediately via Enter/Space and restore a visible keyboard focus target.
		void tick().then(() => exploreButton?.focus({ preventScroll: true }));
	});
</script>

<svelte:window onkeydown={(event) => {
	if (show && !leaving && event.key === 'Tab') {
		event.preventDefault();
		exploreButton?.focus();
	}
}} />

{#if show}
	<div class="splash" class:leaving role="dialog" aria-modal="true" aria-labelledby="splash-title" aria-describedby="splash-description">
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
		<section class="stack" aria-labelledby="splash-title">
			<img src={logo} alt="" class="mark" />
			<div class="name" aria-hidden="true"><span>De</span><span class="f">F</span><span>aketive</span></div>
			<div class="tag"><i></i><span>A SAFER YOU</span><i></i></div>
			<h1 id="splash-title" class="hero-title">Know what buyers really say before you buy.</h1>
			<p id="splash-description" class="hero-description">See what shoppers liked, what went wrong, and possible safety concerns—based on customer reviews.</p>
			<button type="button" class="go" onclick={enter} aria-label="Explore DeFaketive" bind:this={exploreButton}>
				<span>Explore DeFaketive</span>
				<ArrowRightIcon class="go-arrow" size={21} strokeWidth={2.5} aria-hidden="true" />
			</button>
			<p class="hero-note">Review-based guidance, not independent product testing.</p>
		</section>
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
		overflow-x: hidden;
		overflow-y: auto;
		padding: clamp(1rem, 3vmin, 2rem);
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
	/* Frosted paper card: products remain recognizable around the edges,
	   while the message and gold CTA form one clear reading path. */
	.stack {
		position: relative;
		z-index: 1;
		width: min(36rem, 100%);
		box-sizing: border-box;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.65rem;
		padding: clamp(1.35rem, 3vw, 2.35rem);
		border: 1px solid rgba(255, 255, 255, 0.96);
		border-top: 4px solid var(--mustard);
		border-radius: 1.6rem;
		background: rgba(255, 255, 255, 0.94);
		box-shadow: 0 22px 68px rgba(5, 14, 40, 0.35), 0 0 0 1px rgba(11, 31, 77, 0.10);
		-webkit-backdrop-filter: blur(14px);
		backdrop-filter: blur(14px);
		text-align: center;
	}
	.hero-title {
		max-width: 25ch;
		margin: 0.7rem 0 0;
		color: var(--navy);
		font: 800 clamp(1.4rem, 3.2vw, 2.05rem) / 1.18 Inter, system-ui, sans-serif;
		letter-spacing: -0.035em;
		text-wrap: balance;
		animation: up 0.5s ease-out 0.4s both;
	}
	.hero-description {
		max-width: 43ch;
		margin: 0;
		color: #3f4b64;
		font: 450 clamp(0.93rem, 1.55vw, 1.05rem) / 1.55 Inter, system-ui, sans-serif;
		text-wrap: pretty;
		animation: up 0.5s ease-out 0.5s both;
	}
	.hero-note {
		margin: 0.35rem 0 0;
		color: #4e5870;
		font: 500 0.77rem / 1.4 Inter, system-ui, sans-serif;
	}
	.mark {
		width: clamp(3.5rem, 9vw, 4.65rem);
		filter: drop-shadow(0 4px 7px rgba(11, 31, 77, 0.14));
		animation: pop 0.65s cubic-bezier(0.2, 0.9, 0.3, 1.25) 0.1s both;
	}
	.name {
		color: var(--navy);
		font: 900 clamp(1.8rem, 5.5vw, 2.5rem) / 1 'Archivo Black', 'Arial Black', Impact, sans-serif;
		font-style: italic;
		letter-spacing: -0.03em;
		animation: up 0.55s cubic-bezier(0.2, 0.7, 0.2, 1) 0.2s both;
	}
	.f {
		color: var(--mustard);
	}
	.tag {
		display: flex;
		align-items: center;
		gap: 0.8rem;
		color: #293d67;
		font: 800 clamp(0.63rem, 1.65vw, 0.75rem) / 1 Inter, system-ui, sans-serif;
		letter-spacing: 0.34em;
		animation: up 0.55s cubic-bezier(0.2, 0.7, 0.2, 1) 0.3s both;
	}
	.tag i {
		display: block;
		width: clamp(1.5rem, 6vw, 3.5rem);
		height: 2px;
		box-shadow: 0 0 8px rgba(255, 255, 255, 0.95);
		border-radius: 2px;
		background: var(--navy);
		transform-origin: center;
		animation: grow 0.55s ease-out 0.45s both;
	}
	/* One obvious first action: large enough for touch, gold against the navy
	   collage, with a light separation ring so the product photos don't compete. */
	.go {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		margin-top: 0.85rem;
		min-height: 3.75rem;
		min-width: 15rem;
		max-width: calc(100vw - 2.5rem);
		padding: 0.85rem 1.65rem;
		border: 2px solid var(--navy);
		border-radius: 999px;
		background: var(--mustard);
		color: var(--navy);
		font: 800 clamp(1rem, 1.35vw, 1.15rem) / 1.2 Inter, system-ui, sans-serif;
		letter-spacing: 0.01em;
		white-space: nowrap;
		box-shadow: 0 0 0 5px rgba(255, 255, 255, 0.78), 0 14px 28px -7px rgba(5, 14, 40, 0.75);
		cursor: pointer;
		transition: background-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
		animation: up 0.55s ease-out 0.6s both;
	}
	.go:hover {
		background: #ffd064;
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
		.stack {
			border-radius: 1.2rem;
			padding: 1.35rem 1.1rem;
		}
		.go {
			width: min(19rem, 83vw);
		}
	}
	@media (max-height: 650px) {
		.stack {
			gap: 0.4rem;
			padding: 1rem 1.25rem;
		}
		.mark { width: 3.2rem; }
		.hero-title { margin-top: 0.4rem; font-size: 1.35rem; }
		.hero-description { font-size: 0.91rem; line-height: 1.35; }
		.go { min-height: 3.25rem; margin-top: 0.4rem; }
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
		.hero-title,
		.hero-description,
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
