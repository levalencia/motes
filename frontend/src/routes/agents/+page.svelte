<script lang="ts">
	import { goto } from '$app/navigation';
	import { createAgent, deleteAgent, listAgents, listProviders, type Agent, type Provider } from '$lib/api/client';
	import { onMount } from 'svelte';

	let agents = $state<Agent[]>([]);
	let providers = $state<Provider[]>([]);
	let showForm = $state(false);
	let name = $state('');
	let provider_id = $state('');
	let system_prompt = $state('You are a helpful assistant.');
	let error = $state('');
	let loading = $state(false);

	onMount(async () => {
		try {
			[agents, providers] = await Promise.all([listAgents(), listProviders()]);
		} catch (e: any) {
			if (e?.message?.includes('401')) goto('/login');
		}
	});

	async function handleCreate() {
		error = '';
		loading = true;
		try {
			const a = await createAgent({ name, provider_id, system_prompt });
			agents = [...agents, a];
			showForm = false;
			name = '';
			system_prompt = 'You are a helpful assistant.';
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	async function handleDelete(id: string) {
		await deleteAgent(id);
		agents = agents.filter((a) => a.id !== id);
	}
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Dashboard</a>
			<h1 class="text-xl font-bold">Agents</h1>
		</div>
		<button onclick={() => (showForm = !showForm)} class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm">
			{showForm ? 'Cancel' : '+ Create Agent'}
		</button>
	</nav>

	<main class="max-w-4xl mx-auto px-6 py-8">
		{#if showForm}
			<form onsubmit={(e) => { e.preventDefault(); handleCreate(); }} class="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-6 space-y-4">
				<h2 class="text-lg font-semibold">Create Agent</h2>
				{#if providers.length === 0}
					<p class="text-yellow-400 text-sm">You need to <a href="/providers" class="underline">add a provider</a> first.</p>
				{:else}
					<div>
						<label class="block text-sm text-gray-300">Name</label>
						<input bind:value={name} required placeholder="My Assistant" class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white" />
					</div>
					<div>
						<label class="block text-sm text-gray-300">Provider</label>
						<select bind:value={provider_id} required class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white">
							<option value="">Select a provider...</option>
							{#each providers as p}
								<option value={p.id}>{p.name} ({p.model})</option>
							{/each}
						</select>
					</div>
					<div>
						<label class="block text-sm text-gray-300">System Prompt</label>
						<textarea bind:value={system_prompt} rows={4} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white"></textarea>
					</div>
					{#if error}
						<p class="text-red-400 text-sm">{error}</p>
					{/if}
					<button type="submit" disabled={loading} class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-sm">
						{loading ? 'Creating...' : 'Create Agent'}
					</button>
				{/if}
			</form>
		{/if}

		{#if agents.length === 0}
			<div class="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
				<p class="text-gray-400">No agents yet.</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each agents as agent}
					<div class="bg-gray-900 border border-gray-800 rounded-lg p-4 flex justify-between items-center">
						<a href="/dashboard" class="flex-1">
							<h3 class="font-semibold">{agent.name}</h3>
							<p class="text-gray-400 text-sm">{agent.model || agent.provider_name || 'Unknown'}</p>
						</a>
						<div class="flex items-center gap-3">
							<a href="/dashboard" class="text-blue-400 hover:text-blue-300 text-sm">Open →</a>
							<button onclick={() => handleDelete(agent.id)} class="text-red-400 hover:text-red-300 text-sm">Delete</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
