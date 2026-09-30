<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { isAuthenticated } from '$lib/stores/auth';

	let checking = $state(true);

	onMount(async () => {
		// If already logged in, go to dashboard
		if ($isAuthenticated) {
			goto('/dashboard');
			return;
		}

		// Check if setup is complete
		try {
			const res = await fetch('http://localhost:8001/api/auth/setup-status');
			const data = await res.json();
			if (!data.is_setup_complete) {
				goto('/setup');
			} else {
				goto('/login');
			}
		} catch {
			// Backend not reachable — show landing page
			checking = false;
		}
	});
</script>

{#if checking}
	<div class="min-h-screen bg-gray-950 flex items-center justify-center">
		<p class="text-gray-400">Loading...</p>
	</div>
{:else}
	<div class="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 flex flex-col items-center justify-center text-white px-4">
		<div class="max-w-2xl text-center space-y-8">
			<h1 class="text-6xl font-bold tracking-tight">Motes</h1>
			<p class="text-xl text-gray-300">Your agents, your models, your data</p>
			<div class="flex flex-wrap justify-center gap-3 text-sm text-gray-400">
				<span class="px-3 py-1 rounded-full border border-gray-700">Model-agnostic</span>
				<span class="px-3 py-1 rounded-full border border-gray-700">Self-hosted</span>
				<span class="px-3 py-1 rounded-full border border-gray-700">MCP connectors</span>
				<span class="px-3 py-1 rounded-full border border-gray-700">EU/UK friendly</span>
				<span class="px-3 py-1 rounded-full border border-gray-700">Open source</span>
			</div>
			<p class="text-sm text-gray-500">
				Open-source alternative to OpenAI Dots — always-on AI agents that connect to your
				email, calendar, GitHub, and 100+ services.
			</p>
			<p class="text-yellow-400 text-sm">Backend not reachable. Make sure to run <code class="bg-gray-800 px-2 py-1 rounded">make docker-up && make dev</code></p>
		</div>
	</div>
{/if}
