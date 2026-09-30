<script lang="ts">
	import { goto } from '$app/navigation';
	import { listAgents, listProviders, api, type Agent, type Provider } from '$lib/api/client';
	import { clearAuth, username } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	let agents = $state<Agent[]>([]);
	let providers = $state<Provider[]>([]);
	let connectedServices = $state(0);
	let loading = $state(true);

	onMount(async () => {
		try {
			const [a, p, svc] = await Promise.all([
				listAgents(),
				listProviders(),
				api<{ service: string }[]>('/oauth/connected'),
			]);
			agents = a;
			providers = p;
			connectedServices = svc.length;
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	});
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<!-- Top nav -->
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-3">
			<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">M</div>
			<h1 class="text-xl font-bold">Motes</h1>
		</div>
		<div class="flex items-center gap-4">
			<a href="/providers" class="text-sm text-gray-400 hover:text-white">Providers</a>
			<a href="/agents" class="text-sm text-gray-400 hover:text-white">Agents</a>
			<a href="/services" class="text-sm text-gray-400 hover:text-white">Services</a>
			<span class="text-gray-600">|</span>
			<span class="text-gray-400 text-sm">{$username}</span>
			<button onclick={() => { clearAuth(); goto('/login'); }} class="text-sm text-gray-500 hover:text-white">
				Sign out
			</button>
		</div>
	</nav>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="text-gray-500">Loading...</div>
			</div>
		{:else}
			<!-- Stats row -->
			<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
					<div class="flex items-center justify-between">
						<span class="text-xs text-gray-500 uppercase tracking-wider">Agents</span>
						<span class="text-2xl">🤖</span>
					</div>
					<p class="text-3xl font-bold mt-1">{agents.length}</p>
					<a href="/agents" class="text-blue-400 text-xs mt-2 inline-block hover:underline">Manage →</a>
				</div>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
					<div class="flex items-center justify-between">
						<span class="text-xs text-gray-500 uppercase tracking-wider">Providers</span>
						<span class="text-2xl">⚡</span>
					</div>
					<p class="text-3xl font-bold mt-1">{providers.length}</p>
					<a href="/providers" class="text-blue-400 text-xs mt-2 inline-block hover:underline">Manage →</a>
				</div>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
					<div class="flex items-center justify-between">
						<span class="text-xs text-gray-500 uppercase tracking-wider">Services</span>
						<span class="text-2xl">🔌</span>
					</div>
					<p class="text-3xl font-bold mt-1">{connectedServices}</p>
					<a href="/services" class="text-blue-400 text-xs mt-2 inline-block hover:underline">Connect →</a>
				</div>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
					<div class="flex items-center justify-between">
						<span class="text-xs text-gray-500 uppercase tracking-wider">Status</span>
						<span class="text-2xl">🟢</span>
					</div>
					<p class="text-xl font-bold mt-1 text-green-400">All systems online</p>
				</div>
			</div>

			<!-- Agents section -->
			<div class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold">Your Agents</h2>
					<a href="/agents" class="text-sm text-blue-400 hover:underline">+ Create Agent</a>
				</div>

				{#if agents.length === 0}
					<div class="bg-gray-900 border border-gray-800 border-dashed rounded-xl p-12 text-center">
						<p class="text-4xl mb-3">🤖</p>
						<p class="text-gray-400 font-medium">No agents yet</p>
						<p class="text-gray-500 text-sm mt-1">
							{#if providers.length === 0}
								<a href="/providers" class="text-blue-400 hover:underline">Add a provider</a> first, then create an agent.
							{:else}
								<a href="/agents" class="text-blue-400 hover:underline">Create your first agent</a> to get started.
							{/if}
						</p>
					</div>
				{:else}
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
						{#each agents as agent}
							<a
								href="/chat/{agent.id}"
								class="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-blue-500/50 hover:bg-gray-900/80 transition-all group"
							>
								<div class="flex items-start gap-3">
									<div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-lg flex-shrink-0">
										{agent.name[0]}
									</div>
									<div class="flex-1 min-w-0">
										<h3 class="font-semibold group-hover:text-blue-400 transition-colors">{agent.name}</h3>
										<p class="text-gray-500 text-xs mt-0.5">{agent.model || 'Unknown model'}</p>
									</div>
									<div class="w-2 h-2 bg-green-400 rounded-full mt-2 flex-shrink-0" title="Online"></div>
								</div>
								<p class="text-gray-500 text-xs mt-3 line-clamp-2">{agent.system_prompt}</p>
								<div class="flex items-center gap-3 mt-3 text-xs text-gray-600">
									<span>💬 Chat</span>
									<span>🧠 Memory</span>
									<span>🔧 2 tools</span>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Quick actions -->
			<div>
				<h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<a href="/services" class="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition-colors">
						<p class="text-2xl mb-2">📧</p>
						<h3 class="font-medium">Connect Gmail</h3>
						<p class="text-gray-500 text-xs mt-1">Let your agents read and send emails</p>
					</a>
					<a href="/services" class="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition-colors">
						<p class="text-2xl mb-2">📅</p>
						<h3 class="font-medium">Connect Calendar</h3>
						<p class="text-gray-500 text-xs mt-1">Schedule meetings and check availability</p>
					</a>
					<a href="/services" class="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition-colors">
						<p class="text-2xl mb-2">💻</p>
						<h3 class="font-medium">Connect GitHub</h3>
						<p class="text-gray-500 text-xs mt-1">Manage issues, PRs, and repositories</p>
					</a>
				</div>
			</div>
		{/if}
	</main>
</div>
