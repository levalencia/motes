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

	interface CatalogEntry {
		name: string;
		description: string;
		category: string;
		built_in?: boolean;
		requires_oauth?: boolean;
		macos_only?: boolean;
		env_vars?: string[];
		coming_soon?: boolean;
	}

	let services = $state<OAuthService[]>([]);
	let connected = $state<ConnectedService[]>([]);
	let oauthApps = $state<OAuthApp[]>([]);
	let catalog = $state<CatalogEntry[]>([]);
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
		gmail: '📧', calendar: '📅', github: '💻', slack: '💬',
		weather: '🌤️', reminders: '✅', notes: '📝', maps: '🗺️',
		news: '📰', files: '📁', todoist: '☑️', notion: '📓',
		spotify: '🎵', homeassistant: '🏠', outlook: '📮',
		flights: '✈️', telegram: '📱', drive: '💾', whatsapp: '💬',
	};

	// Setup instructions for each API-key service
	const serviceGuides: Record<string, { steps: string[]; link: string }> = {
		github: {
			steps: [
				'Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)',
				'Click "Generate new token (classic)"',
				'Select scopes: repo, read:user, read:org',
				'Copy the token (starts with ghp_)',
			],
			link: 'https://github.com/settings/tokens',
		},
		slack: {
			steps: [
				'Go to api.slack.com/apps → Create New App → From scratch',
				'Under OAuth & Permissions, add scopes: channels:read, chat:write, channels:history',
				'Install the app to your workspace',
				'Copy the Bot User OAuth Token (starts with xoxb-)',
			],
			link: 'https://api.slack.com/apps',
		},
		todoist: {
			steps: [
				'Go to todoist.com → Settings → Integrations → Developer',
				'Copy your API token',
			],
			link: 'https://todoist.com/app/settings/integrations/developer',
		},
		notion: {
			steps: [
				'Go to notion.so/my-integrations → Create new integration',
				'Give it a name and select your workspace',
				'Copy the Internal Integration Secret (starts with ntn_)',
				'Share your Notion pages with the integration',
			],
			link: 'https://www.notion.so/my-integrations',
		},
		spotify: {
			steps: [
				'Go to developer.spotify.com/dashboard → Create app',
				'Set redirect URI to http://localhost:8001/callback',
				'Use the Client Credentials flow or get a user token',
				'Copy the access token',
			],
			link: 'https://developer.spotify.com/dashboard',
		},
		homeassistant: {
			steps: [
				'Open your Home Assistant instance',
				'Go to Profile → Long-Lived Access Tokens → Create Token',
				'Copy the token and your HA URL (e.g., http://homeassistant.local:8123)',
			],
			link: '',
		},
		outlook: {
			steps: [
				'Go to Azure Portal → App Registrations → New registration',
				'Add Microsoft Graph permissions: Mail.Read, Mail.Send, Calendars.Read',
				'Get an access token via OAuth2 authorization code flow',
			],
			link: 'https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps',
		},
		flights: {
			steps: [
				'Go to developers.amadeus.com → Register for free',
				'Create a new app in the dashboard',
				'Copy the API Key and API Secret (test environment is free)',
			],
			link: 'https://developers.amadeus.com/',
		},
		telegram: {
			steps: [
				'Message @BotFather on Telegram',
				'Send /newbot and follow the prompts',
				'Copy the bot token',
				'Send a message to your bot, then get your chat ID from api.telegram.org/bot<TOKEN>/getUpdates',
			],
			link: 'https://t.me/BotFather',
		},
	};

	let configuringService = $state('');
	let keyInputs = $state<Record<string, string>>({});
	let savingKey = $state(false);
	let serviceStatuses = $state<Record<string, boolean>>({});

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
		} catch (e: any) {
			if (e?.message?.includes('401')) goto('/login');
		}

		// Load catalog separately (doesn't need OAuth to be configured)
		try {
			catalog = await api<CatalogEntry[]>('/mcp/catalog');
		} catch {
			// Catalog is non-critical
		}

		// Load service key statuses
		try {
			const statuses = await api<{service: string; configured: boolean}[]>('/service-keys');
			for (const s of statuses) {
				serviceStatuses[s.service] = s.configured;
			}
		} catch {
			// Non-critical
		}

		loading = false;
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
									<a
										href="/services/setup/{svc.provider}"
										class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm w-full text-gray-300 text-center block"
									>
										⚙️ Setup {svc.provider} → step-by-step guide
									</a>
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

			<!-- All Integrations (from catalog) -->
			<div class="mt-10">
				<h2 class="text-lg font-semibold mb-2" style="color: var(--text-primary);">All Integrations ({catalog.length})</h2>
				<p class="text-sm mb-4" style="color: var(--text-secondary);">
					Built-in tools work instantly. Others need an API key set in your environment.
				</p>

				<!-- Built-in (free) -->
				<h3 class="text-sm font-medium mb-3" style="color: var(--text-muted);">✅ BUILT-IN (free, no setup)</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
					{#each catalog.filter(c => c.built_in) as item}
						<div class="rounded-xl p-4" style="background: var(--bg-card); border: 1px solid var(--border);">
							<div class="flex items-center gap-2 mb-1">
								<span class="text-green-500 text-xs">●</span>
								<span class="font-medium text-sm" style="color: var(--text-primary);">{item.name}</span>
								{#if item.macos_only}
									<span class="text-xs px-1.5 py-0.5 rounded" style="background: var(--bg-hover); color: var(--text-muted);">macOS</span>
								{/if}
							</div>
							<p class="text-xs" style="color: var(--text-secondary);">{item.description}</p>
						</div>
					{/each}
				</div>

				<!-- API key required -->
				<h3 class="text-sm font-medium mb-3" style="color: var(--text-muted);">🔑 REQUIRES API KEY</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
					{#each catalog.filter(c => !c.built_in && !c.coming_soon && c.env_vars) as item}
						{@const svcKey = item.name.toLowerCase().replace(/[^a-z]/g, '').replace('office365', 'outlook').replace('hotels', 'flights')}
						<div class="rounded-xl p-4" style="background: var(--bg-card); border: 1px solid var(--border);">
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs">{serviceStatuses[svcKey] ? '🟢' : '🟡'}</span>
								<span class="font-medium text-sm" style="color: var(--text-primary);">{item.name}</span>
								{#if serviceStatuses[svcKey]}
									<span class="text-xs px-1.5 py-0.5 rounded-full" style="background: #10B98120; color: #10B981;">Connected</span>
								{/if}
							</div>
							<p class="text-xs mb-3" style="color: var(--text-secondary);">{item.description}</p>

							{#if configuringService === svcKey}
								<!-- Setup guide -->
								{#if serviceGuides[svcKey]}
									<div class="mb-3 text-xs space-y-1" style="color: var(--text-secondary);">
										{#each serviceGuides[svcKey].steps as step, i}
											<p>{i + 1}. {step}</p>
										{/each}
										{#if serviceGuides[svcKey].link}
											<a href={serviceGuides[svcKey].link} target="_blank" class="text-xs underline" style="color: var(--accent);">
												Open {item.name} →
											</a>
										{/if}
									</div>
								{/if}
								<!-- Key inputs -->
								<div class="space-y-2">
									{#each item.env_vars || [] as envVar}
										<div>
											<label class="text-xs font-mono block mb-1" style="color: var(--text-muted);">{envVar}</label>
											<input
												type="password"
												placeholder="Paste your key..."
												value={keyInputs[envVar] || ''}
												oninput={(e) => { keyInputs[envVar] = (e.target as HTMLInputElement).value; }}
												class="w-full px-3 py-2 rounded-lg text-xs outline-none"
												style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
											/>
										</div>
									{/each}
									<div class="flex gap-2 mt-2">
										<button
											onclick={async () => {
												savingKey = true;
												try {
													await api('/service-keys', {
														method: 'POST',
														body: JSON.stringify({ service: svcKey, keys: keyInputs }),
													});
													serviceStatuses[svcKey] = true;
													configuringService = '';
													keyInputs = {};
												} catch (e: any) { error = e.message; }
												savingKey = false;
											}}
											disabled={savingKey}
											class="px-3 py-1.5 rounded-lg text-xs font-medium text-white"
											style="background: var(--accent);"
										>
											{savingKey ? 'Saving...' : 'Save'}
										</button>
										<button
											onclick={() => { configuringService = ''; }}
											class="px-3 py-1.5 rounded-lg text-xs"
											style="color: var(--text-muted);"
										>
											Cancel
										</button>
									</div>
								</div>
							{:else}
								<button
									onclick={() => { configuringService = svcKey; keyInputs = {}; }}
									class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
									style="background: {serviceStatuses[svcKey] ? 'var(--bg-hover)' : 'var(--accent)'}; color: {serviceStatuses[svcKey] ? 'var(--text-secondary)' : 'white'};"
								>
									{serviceStatuses[svcKey] ? '⚙️ Reconfigure' : '🔧 Setup'}
								</button>
							{/if}
						</div>
					{/each}
				</div>

				<!-- Coming soon -->
				{#if catalog.filter(c => c.coming_soon).length > 0}
					<h3 class="text-sm font-medium mb-3" style="color: var(--text-muted);">🔜 COMING SOON</h3>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
						{#each catalog.filter(c => c.coming_soon) as item}
							<div class="rounded-xl p-4 opacity-50" style="background: var(--bg-card); border: 1px solid var(--border);">
								<div class="flex items-center gap-2 mb-1">
									<span class="text-gray-500 text-xs">●</span>
									<span class="font-medium text-sm" style="color: var(--text-primary);">{item.name}</span>
								</div>
								<p class="text-xs" style="color: var(--text-secondary);">{item.description}</p>
							</div>
						{/each}
					</div>
				{/if}
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
