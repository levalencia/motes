<script lang="ts">
	import { goto } from '$app/navigation';
	import { createProvider, deleteProvider, listProviders, type Provider } from '$lib/api/client';
	import { onMount } from 'svelte';

	let providers = $state<Provider[]>([]);
	let showForm = $state(false);
	let name = $state('');
	let base_url = $state('');
	let api_key = $state('');
	let model = $state('');
	let error = $state('');
	let loading = $state(false);

	onMount(async () => {
		try {
			providers = await listProviders();
		} catch (e: any) {
			if (e?.message?.includes('401')) goto('/login');
		}
	});

	async function handleCreate() {
		error = '';
		loading = true;
		try {
			const p = await createProvider({ name, base_url, api_key, model });
			providers = [...providers, p];
			showForm = false;
			name = base_url = api_key = model = '';
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}

	async function handleDelete(id: string) {
		try {
			await deleteProvider(id);
			providers = providers.filter((p) => p.id !== id);
		} catch (e: any) {
			error = e.message;
		}
	}
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Dashboard</a>
			<h1 class="text-xl font-bold">Providers</h1>
		</div>
		<button onclick={() => (showForm = !showForm)} class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm">
			{showForm ? 'Cancel' : '+ Add Provider'}
		</button>
	</nav>

	<main class="max-w-4xl mx-auto px-6 py-8">
		{#if showForm}
			<form onsubmit={(e) => { e.preventDefault(); handleCreate(); }} class="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-6 space-y-4">
				<h2 class="text-lg font-semibold">Add OpenAI-compatible Provider</h2>
				<p class="text-sm text-gray-400">Motes will test the connection before saving.</p>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label class="block text-sm text-gray-300">Name</label>
						<input bind:value={name} required placeholder="My GPT-4" class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white" />
					</div>
					<div>
						<label class="block text-sm text-gray-300">Model</label>
						<input bind:value={model} required placeholder="gpt-4o" class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white" />
					</div>
					<div class="md:col-span-2">
						<label class="block text-sm text-gray-300">Base URL</label>
						<input bind:value={base_url} required placeholder="https://api.openai.com/v1" class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white" />
					</div>
					<div class="md:col-span-2">
						<label class="block text-sm text-gray-300">API Key</label>
						<input bind:value={api_key} required type="password" placeholder="sk-..." class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white" />
					</div>
				</div>
				{#if error}
					<p class="text-red-400 text-sm">{error}</p>
				{/if}
				<button type="submit" disabled={loading} class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-sm">
					{loading ? 'Testing & saving...' : 'Test & Save'}
				</button>
			</form>
		{/if}

		{#if providers.length === 0}
			<div class="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
				<p class="text-gray-400">No providers configured yet.</p>
				<p class="text-gray-500 text-sm mt-1">Add an OpenAI-compatible endpoint to get started.</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each providers as provider}
					<div class="bg-gray-900 border border-gray-800 rounded-lg p-4 flex justify-between items-center">
						<div>
							<h3 class="font-semibold">{provider.name}</h3>
							<p class="text-gray-400 text-sm">{provider.model} · {provider.base_url}</p>
						</div>
						<div class="flex items-center gap-3">
							{#if provider.is_verified}
								<span class="text-green-400 text-xs">✓ Verified</span>
							{/if}
							<button onclick={() => handleDelete(provider.id)} class="text-red-400 hover:text-red-300 text-sm">Delete</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
