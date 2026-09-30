<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api } from '$lib/api/client';

	interface OAuthService {
		provider: string;
		service: string;
		label: string;
		is_connected: boolean;
		is_configured: boolean;
	}

	interface ConnectedService {
		service: string;
		provider: string;
		account_email: string;
		scopes: string;
	}

	interface OAuthApp {
		provider: string;
		client_id: string;
		is_configured: boolean;
	}

	let services = $state<OAuthService[]>([]);
	let connected = $state<ConnectedService[]>([]);
	let oauthApps = $state<OAuthApp[]>([]);
	let loading = $state(true);
	let error = $state('');
	let justConnected = $state('');

	// Admin setup form
	let showAdminSetup = $state(false);
	let adminProvider = $state('google');
	let adminClientId = $state('');
	let adminClientSecret = $state('');
	let adminSaving = $state(false);

	const serviceIcons: Record<string, string> = {
		gmail: '📧',
		calendar: '📅',
		github: '💻',
		slack: '💬',
	};

	const providerSetupHelp: Record<string, string> = {
		google: 'Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client',
		github: 'GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App',
		slack: 'api.slack.com → Your Apps → Create New App → OAuth & Permissions',
	};

	onMount(async () => {
		// Check for success redirect
		const connectedParam = $page.url.searchParams.get('connected');
		if (connectedParam) {
			justConnected = connectedParam;
			// Clean URL
			window.history.replaceState({}, '', '/services');
		}

		try {
			const [svc, conn, apps] = await Promise.all([
				api<OAuthService[]>('/oauth/services'),
				api<ConnectedService[]>('/oauth/connected'),
				api<OAuthApp[]>('/oauth/apps'),
			]);
			services = svc;
			connected = conn;
			oauthApps = apps;
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	});

	async function connectService(provider: string, service: string) {
		error = '';
		try {
			const result = await api<{ auth_url: string }>(
				`/oauth/connect/${provider}/${service}`
			);
			// Redirect to consent screen
			window.location.href = result.auth_url;
		} catch (e: any) {
			error = e.message;
		}
	}

	async function disconnectService(service: string) {
		try {
			await api(`/oauth/connected/${service}`, { method: 'DELETE' });
			connected = connected.filter((c) => c.service !== service);
			services = services.map((s) =>
				s.service === service ? { ...s, is_connected: false } : s
			);
		} catch (e: any) {
			error = e.message;
		}
	}

	async function saveAdminConfig() {
		adminSaving = true;
		error = '';
		try {
			await api('/oauth/apps', {
				method: 'POST',
				body: JSON.stringify({
					provider: adminProvider,
					client_id: adminClientId,
					client_secret: adminClientSecret,
				}),
			});
			oauthApps = await api<OAuthApp[]>('/oauth/apps');
			services = await api<OAuthService[]>('/oauth/services');
			showAdminSetup = false;
			adminClientId = '';
			adminClientSecret = '';
		} catch (e: any) {
			error = e.message;
		} finally {
			adminSaving = false;
		}
	}

	function getConnectedInfo(service: string): ConnectedService | undefined {
		return connected.find((c) => c.service === service);
	}

	function isProviderConfigured(provider: string): boolean {
		return oauthApps.some((a) => a.provider === provider);
	}
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Dashboard</a>
			<h1 class="text-xl font-bold">Connected Services</h1>
		</div>
		<button
			onclick={() => (showAdminSetup = !showAdminSetup)}
			class="text-sm text-gray-400 hover:text-white px-3 py-1 border border-gray-700 rounded hover:border-gray-500"
		>
			⚙️ OAuth Settings
		</button>
	</nav>

	<main class="max-w-5xl mx-auto px-6 py-8">
		{#if loading}
			<p class="text-gray-400">Loading services...</p>
		{:else}
			{#if justConnected}
				<div class="bg-green-950 border border-green-800 rounded-lg px-4 py-3 mb-6 text-sm text-green-400">
					✓ Successfully connected {justConnected}!
				</div>
			{/if}

			{#if error}
				<div class="bg-red-950 border border-red-900 rounded-lg px-4 py-3 mb-6 text-sm text-red-400">
					{error}
				</div>
			{/if}

			<!-- Admin OAuth setup -->
			{#if showAdminSetup}
				<div class="bg-gray-900 border border-yellow-500/30 rounded-xl p-6 mb-8">
					<h2 class="text-lg font-semibold mb-1">⚙️ OAuth Provider Setup</h2>
					<p class="text-gray-400 text-sm mb-4">
						One-time setup: add your OAuth credentials so users can connect with one click.
					</p>

					<div class="space-y-4">
						<div>
							<label for="admin-provider" class="block text-sm text-gray-300">Provider</label>
							<select
								id="admin-provider"
								bind:value={adminProvider}
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
							>
								<option value="google">Google (Gmail + Calendar)</option>
								<option value="github">GitHub</option>
								<option value="slack">Slack</option>
							</select>
							<p class="text-gray-600 text-xs mt-1">{providerSetupHelp[adminProvider]}</p>
						</div>
						<div>
							<label for="admin-client-id" class="block text-sm text-gray-300">Client ID</label>
							<input
								id="admin-client-id"
								bind:value={adminClientId}
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
							/>
						</div>
						<div>
							<label for="admin-client-secret" class="block text-sm text-gray-300">Client Secret</label>
							<input
								id="admin-client-secret"
								type="password"
								bind:value={adminClientSecret}
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
							/>
						</div>
						<p class="text-gray-600 text-xs">
							Redirect URI: <code class="bg-gray-800 px-1 rounded">http://localhost:8001/api/oauth/callback/{adminProvider}</code>
						</p>
					</div>
					<div class="flex gap-3 mt-5">
						<button
							onclick={saveAdminConfig}
							disabled={adminSaving || !adminClientId || !adminClientSecret}
							class="px-6 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
						>
							{adminSaving ? 'Saving...' : 'Save Credentials'}
						</button>
						<button
							onclick={() => (showAdminSetup = false)}
							class="px-6 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm"
						>
							Cancel
						</button>
					</div>

					{#if oauthApps.length > 0}
						<div class="mt-4 pt-4 border-t border-gray-800">
							<p class="text-xs text-gray-500 mb-2">Configured providers:</p>
							<div class="flex gap-2">
								{#each oauthApps as app}
									<span class="text-xs bg-green-900/50 text-green-400 px-2 py-1 rounded">
										✓ {app.provider}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Connected services -->
			{#if connected.length > 0}
				<div class="mb-10">
					<h2 class="text-lg font-semibold mb-4">Connected ({connected.length})</h2>
					<div class="space-y-3">
						{#each connected as conn}
							<div class="bg-gray-900 border border-green-900/50 rounded-xl p-4 flex items-center justify-between">
								<div class="flex items-center gap-3">
									<div class="w-10 h-10 bg-green-900/50 border border-green-800 rounded-lg flex items-center justify-center text-lg">
										{serviceIcons[conn.service] || '🔌'}
									</div>
									<div>
										<h3 class="font-medium capitalize">{conn.service}</h3>
										<p class="text-gray-500 text-xs">
											{conn.account_email || conn.provider}
										</p>
									</div>
								</div>
								<div class="flex items-center gap-3">
									<span class="text-green-400 text-xs flex items-center gap-1">
										<span class="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
										Active
									</span>
									<button
										onclick={() => disconnectService(conn.service)}
										class="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded border border-red-900 hover:border-red-700"
									>
										Disconnect
									</button>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Available services -->
			<div>
				<h2 class="text-lg font-semibold mb-2">Available Services</h2>
				<p class="text-gray-500 text-sm mb-4">
					Click Connect to sign in with your account. No API keys needed.
				</p>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					{#each services as svc}
						<div class="bg-gray-900 border border-gray-800 rounded-xl p-5 {svc.is_connected ? 'opacity-60' : ''}">
							<div class="flex items-start gap-3">
								<div class="w-10 h-10 bg-gray-800 border border-gray-700 rounded-lg flex items-center justify-center text-lg flex-shrink-0">
									{serviceIcons[svc.service] || '🔌'}
								</div>
								<div class="flex-1">
									<h3 class="font-semibold">{svc.label}</h3>
									<p class="text-gray-500 text-xs mt-0.5">via {svc.provider}</p>
								</div>
							</div>
							<div class="mt-4">
								{#if svc.is_connected}
									<span class="text-green-400 text-sm">✓ Connected</span>
								{:else if !svc.is_configured}
									<button
										onclick={() => { showAdminSetup = true; adminProvider = svc.provider; }}
										class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm w-full text-gray-300"
									>
										⚙️ Configure {svc.provider} first
									</button>
								{:else}
									<button
										onclick={() => connectService(svc.provider, svc.service)}
										class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium w-full"
									>
										Connect {svc.label}
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Security note -->
			<div class="mt-8 bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-sm text-gray-500">
				<p class="font-medium text-gray-400 mb-1">🔒 How it works</p>
				<p>
					When you click Connect, you're redirected to the service's own sign-in page (Google, GitHub, etc.).
					Motes never sees your password. The service gives Motes a limited access token which is stored
					encrypted on your server. You can disconnect at any time.
				</p>
			</div>
		{/if}
	</main>
</div>
