<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	interface CatalogEntry {
		name: string;
		description: string;
		transport: string;
		command: string;
		env_vars: string[];
		category: string;
	}

	interface ConnectedServer {
		id: string;
		name: string;
		description: string;
		transport: string;
		command: string;
		url: string;
		is_enabled: boolean;
	}

	let catalog = $state<CatalogEntry[]>([]);
	let connected = $state<ConnectedServer[]>([]);
	let loading = $state(true);
	let connecting = $state<string | null>(null);
	let error = $state('');

	// Setup form state
	let showSetupFor = $state<CatalogEntry | null>(null);
	let envValues = $state<Record<string, string>>({});

	const categoryIcons: Record<string, string> = {
		email: '📧',
		calendar: '📅',
		development: '💻',
		communication: '💬',
		utility: '📁',
		search: '🔍',
	};

	const envVarLabels: Record<string, string> = {
		GMAIL_OAUTH_CLIENT_ID: 'Google OAuth Client ID',
		GMAIL_OAUTH_CLIENT_SECRET: 'Google OAuth Client Secret',
		GOOGLE_OAUTH_CLIENT_ID: 'Google OAuth Client ID',
		GOOGLE_OAUTH_CLIENT_SECRET: 'Google OAuth Client Secret',
		GITHUB_PERSONAL_ACCESS_TOKEN: 'GitHub Personal Access Token',
		SLACK_BOT_TOKEN: 'Slack Bot Token',
		BRAVE_API_KEY: 'Brave Search API Key',
	};

	const envVarHelp: Record<string, string> = {
		GMAIL_OAUTH_CLIENT_ID: 'Get from Google Cloud Console → APIs → Credentials',
		GMAIL_OAUTH_CLIENT_SECRET: 'Get from Google Cloud Console → APIs → Credentials',
		GOOGLE_OAUTH_CLIENT_ID: 'Get from Google Cloud Console → APIs → Credentials',
		GOOGLE_OAUTH_CLIENT_SECRET: 'Get from Google Cloud Console → APIs → Credentials',
		GITHUB_PERSONAL_ACCESS_TOKEN: 'GitHub → Settings → Developer Settings → Personal Access Tokens',
		SLACK_BOT_TOKEN: 'Slack API → Your Apps → OAuth & Permissions → Bot Token',
		BRAVE_API_KEY: 'Get from brave.com/search/api/',
	};

	onMount(async () => {
		try {
			const [cat, srv] = await Promise.all([
				api<CatalogEntry[]>('/mcp/catalog'),
				api<ConnectedServer[]>('/mcp/servers'),
			]);
			catalog = cat;
			connected = srv;
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	});

	function startSetup(entry: CatalogEntry) {
		showSetupFor = entry;
		envValues = {};
		error = '';
		// Pre-fill empty values
		for (const v of entry.env_vars) {
			envValues[v] = '';
		}
	}

	function cancelSetup() {
		showSetupFor = null;
		envValues = {};
		error = '';
	}

	async function connectService() {
		if (!showSetupFor) return;
		const entry = showSetupFor;

		// Validate all required env vars are filled
		for (const v of entry.env_vars) {
			if (!envValues[v]?.trim()) {
				error = `${envVarLabels[v] || v} is required`;
				return;
			}
		}

		connecting = entry.name;
		error = '';
		try {
			const server = await api<ConnectedServer>('/mcp/servers', {
				method: 'POST',
				body: JSON.stringify({
					name: entry.name,
					description: entry.description,
					transport: entry.transport,
					command: entry.command,
					env_json: JSON.stringify(envValues),
				}),
			});
			connected = [...connected, server];
			showSetupFor = null;
			envValues = {};
		} catch (e: any) {
			error = e.message;
		} finally {
			connecting = null;
		}
	}

	async function toggleService(id: string, enabled: boolean) {
		try {
			await api(`/mcp/servers/${id}/toggle?enabled=${enabled}`, { method: 'POST' });
			connected = connected.map((s) => (s.id === id ? { ...s, is_enabled: enabled } : s));
		} catch (e: any) {
			error = e.message;
		}
	}

	async function removeService(id: string) {
		try {
			await api(`/mcp/servers/${id}`, { method: 'DELETE' });
			connected = connected.filter((s) => s.id !== id);
		} catch (e: any) {
			error = e.message;
		}
	}

	function isConnected(name: string): boolean {
		return connected.some((s) => s.name === name);
	}
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Dashboard</a>
			<h1 class="text-xl font-bold">Connected Services</h1>
		</div>
	</nav>

	<main class="max-w-5xl mx-auto px-6 py-8">
		{#if loading}
			<p class="text-gray-400">Loading services...</p>
		{:else}
			{#if error && !showSetupFor}
				<div class="bg-red-950 border border-red-900 rounded-lg px-4 py-3 mb-6 text-sm text-red-400">
					{error}
				</div>
			{/if}

			<!-- Setup modal/form -->
			{#if showSetupFor}
				<div class="bg-gray-900 border border-blue-500/50 rounded-xl p-6 mb-8">
					<div class="flex items-center gap-3 mb-4">
						<div class="w-10 h-10 bg-blue-900/50 border border-blue-800 rounded-lg flex items-center justify-center text-lg">
							{categoryIcons[showSetupFor.category] || '🔌'}
						</div>
						<div>
							<h2 class="text-lg font-semibold">Connect {showSetupFor.name}</h2>
							<p class="text-gray-400 text-sm">{showSetupFor.description}</p>
						</div>
					</div>

					{#if showSetupFor.env_vars.length === 0}
						<p class="text-gray-400 text-sm mb-4">No credentials needed — this service works out of the box.</p>
					{:else}
						<p class="text-gray-400 text-sm mb-4">Enter your credentials. These are stored encrypted and never shared.</p>
						<div class="space-y-4">
							{#each showSetupFor.env_vars as envVar}
								<div>
									<label for={envVar} class="block text-sm text-gray-300 font-medium">
										{envVarLabels[envVar] || envVar}
									</label>
									<input
										id={envVar}
										type="password"
										bind:value={envValues[envVar]}
										placeholder={envVar}
										class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
									/>
									{#if envVarHelp[envVar]}
										<p class="text-gray-600 text-xs mt-1">{envVarHelp[envVar]}</p>
									{/if}
								</div>
							{/each}
						</div>
					{/if}

					{#if error}
						<p class="text-red-400 text-sm mt-3">{error}</p>
					{/if}

					<div class="flex gap-3 mt-5">
						<button
							onclick={connectService}
							disabled={connecting !== null}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
						>
							{connecting ? 'Connecting...' : `Connect ${showSetupFor.name}`}
						</button>
						<button
							onclick={cancelSetup}
							class="px-6 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300"
						>
							Cancel
						</button>
					</div>
				</div>
			{/if}

			<!-- Connected services -->
			{#if connected.length > 0}
				<div class="mb-10">
					<h2 class="text-lg font-semibold mb-4">Active Services ({connected.length})</h2>
					<div class="space-y-3">
						{#each connected as server}
							<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
								<div class="flex items-center gap-3">
									<div class="w-10 h-10 bg-green-900/50 border border-green-800 rounded-lg flex items-center justify-center text-lg">
										{categoryIcons[catalog.find((c) => c.name === server.name)?.category || ''] || '🔌'}
									</div>
									<div>
										<h3 class="font-medium">{server.name}</h3>
										<p class="text-gray-500 text-xs">{server.description || server.command}</p>
									</div>
								</div>
								<div class="flex items-center gap-3">
									{#if server.is_enabled}
										<span class="text-green-400 text-xs flex items-center gap-1">
											<span class="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
											Connected
										</span>
									{:else}
										<span class="text-yellow-400 text-xs">Paused</span>
									{/if}
									<button
										onclick={() => toggleService(server.id, !server.is_enabled)}
										class="text-xs text-gray-400 hover:text-white px-2 py-1 rounded border border-gray-700 hover:border-gray-500"
									>
										{server.is_enabled ? 'Pause' : 'Resume'}
									</button>
									<button
										onclick={() => removeService(server.id)}
										class="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded border border-red-900 hover:border-red-700"
									>
										Remove
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Service catalog -->
			<div>
				<h2 class="text-lg font-semibold mb-2">Service Catalog</h2>
				<p class="text-gray-500 text-sm mb-4">Connect services to give your agents superpowers. MCP-based, community-extensible.</p>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					{#each catalog as entry}
						{@const alreadyConnected = isConnected(entry.name)}
						<div class="bg-gray-900 border border-gray-800 rounded-xl p-5 {alreadyConnected ? 'opacity-60' : ''}">
							<div class="flex items-start gap-3">
								<div class="w-10 h-10 bg-gray-800 border border-gray-700 rounded-lg flex items-center justify-center text-lg flex-shrink-0">
									{categoryIcons[entry.category] || '🔌'}
								</div>
								<div class="flex-1">
									<div class="flex items-center justify-between">
										<h3 class="font-semibold">{entry.name}</h3>
										<span class="text-xs text-gray-600 px-2 py-0.5 bg-gray-800 rounded">{entry.category}</span>
									</div>
									<p class="text-gray-400 text-sm mt-1">{entry.description}</p>
									{#if entry.env_vars.length > 0}
										<p class="text-gray-600 text-xs mt-2">
											Requires: {entry.env_vars.map(v => envVarLabels[v] || v).join(', ')}
										</p>
									{:else}
										<p class="text-green-600 text-xs mt-2">No credentials needed</p>
									{/if}
								</div>
							</div>
							<div class="mt-4">
								{#if alreadyConnected}
									<span class="text-green-400 text-sm">✓ Connected</span>
								{:else}
									<button
										onclick={() => startSetup(entry)}
										class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium w-full"
									>
										Connect {entry.name}
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Info note -->
			<div class="mt-8 bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-sm text-gray-500">
				<p class="font-medium text-gray-400 mb-1">🔒 About credentials</p>
				<p>Your API keys and tokens are stored encrypted on your server. Motes is self-hosted — credentials never leave your infrastructure. Each service uses the <a href="https://modelcontextprotocol.io" target="_blank" rel="noopener" class="text-blue-400 hover:underline">Model Context Protocol (MCP)</a> standard.</p>
			</div>
		{/if}
	</main>
</div>
