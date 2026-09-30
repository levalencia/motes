<script lang="ts">
	import { goto } from '$app/navigation';
	import { listAgents, listProviders, type Agent, type Provider } from '$lib/api/client';
	import { clearAuth, username } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	let agents = $state<Agent[]>([]);
	let providers = $state<Provider[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			[agents, providers] = await Promise.all([listAgents(), listProviders()]);
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	});
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<h1 class="text-xl font-bold">Motes</h1>
		<div class="flex items-center gap-4">
			<span class="text-gray-400 text-sm">{$username}</span>
			<button onclick={() => { clearAuth(); goto('/login'); }} class="text-sm text-gray-400 hover:text-white">
				Sign out
			</button>
		</div>
	</nav>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if loading}
			<p class="text-gray-400">Loading...</p>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
				<div class="bg-gray-900 border border-gray-800 rounded-lg p-6">
					<h3 class="text-sm text-gray-400 uppercase tracking-wide">Providers</h3>
					<p class="text-3xl font-bold mt-2">{providers.length}</p>
					<a href="/providers" class="text-blue-400 text-sm mt-2 inline-block hover:underline">Manage →</a>
				</div>
				<div class="bg-gray-900 border border-gray-800 rounded-lg p-6">
					<h3 class="text-sm text-gray-400 uppercase tracking-wide">Agents</h3>
					<p class="text-3xl font-bold mt-2">{agents.length}</p>
					<a href="/agents" class="text-blue-400 text-sm mt-2 inline-block hover:underline">Manage →</a>
				</div>
				<div class="bg-gray-900 border border-gray-800 rounded-lg p-6">
					<h3 class="text-sm text-gray-400 uppercase tracking-wide">Status</h3>
					<p class="text-3xl font-bold mt-2 text-green-400">Online</p>
				</div>
			</div>

			<h2 class="text-xl font-semibold mb-4">Your Agents</h2>
			{#if agents.length === 0}
				<div class="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
					<p class="text-gray-400">No agents yet.</p>
					<p class="text-gray-500 text-sm mt-1">
						{#if providers.length === 0}
							<a href="/providers" class="text-blue-400 hover:underline">Add a provider</a> first, then create an agent.
						{:else}
							<a href="/agents" class="text-blue-400 hover:underline">Create your first agent</a>
						{/if}
					</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					{#each agents as agent}
						<a
							href="/chat/{agent.id}"
							class="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-600 transition-colors"
						>
							<h3 class="font-semibold">{agent.name}</h3>
							<p class="text-gray-400 text-sm mt-1">{agent.model || 'Unknown model'}</p>
							<p class="text-gray-500 text-xs mt-2 line-clamp-2">{agent.system_prompt}</p>
						</a>
					{/each}
				</div>
			{/if}
		{/if}
	</main>
</div>
