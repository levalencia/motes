<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api, configureSlackWebhook, configureTelegramWebhook, listAgents } from '$lib/api/client';
	import TopNav from '$lib/components/TopNav.svelte';

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

	let catalog = $state<CatalogEntry[]>([]);
	let connectedOAuth = $state<string[]>([]);  // service names like 'gmail', 'calendar'
	let serviceStatuses = $state<Record<string, boolean>>({});
	let loading = $state(true);
	let error = $state('');
	let successMessage = $state('');
	let configuringService = $state('');
	let keyInputs = $state<Record<string, string>>({});
	let savingKey = $state(false);

	// Slack/Telegram webhook config
	let defaultAgentId = $state('');
	let slackChannelId = $state('');
	let slackSaving = $state(false);
	let slackSaved = $state(false);
	let telegramChatId = $state('');
	let telegramSaving = $state(false);
	let telegramSaved = $state(false);
	const webhookBaseUrl = 'http://localhost:8001/api/webhooks';

	// Map catalog names to service keys and OAuth names
	const catalogToKey: Record<string, string> = {
		'Gmail': 'gmail', 'Google Calendar': 'calendar',
		'GitHub': 'github', 'Slack': 'slack', 'Todoist': 'todoist',
		'Notion': 'notion', 'Spotify': 'spotify', 'Home Assistant': 'homeassistant',
		'Outlook / Office 365': 'outlook', 'Flights & Hotels': 'flights',
		'Telegram': 'telegram',
	};

	const serviceGuides: Record<string, { steps: string[]; link: string }> = {
		github: {
			steps: ['Go to GitHub → Settings → Developer settings → Personal access tokens', 'Generate new token (classic) with scopes: repo, read:user', 'Copy the token (starts with ghp_)'],
			link: 'https://github.com/settings/tokens',
		},
		slack: {
			steps: ['Go to api.slack.com/apps → Create New App', 'Add scopes: channels:read, chat:write, channels:history', 'Install to workspace, copy Bot Token (xoxb-)'],
			link: 'https://api.slack.com/apps',
		},
		todoist: { steps: ['Go to Todoist Settings → Integrations → Developer', 'Copy your API token'], link: 'https://todoist.com/app/settings/integrations/developer' },
		notion: { steps: ['Go to notion.so/my-integrations → Create integration', 'Copy the secret (ntn_...)', 'Share your pages with the integration'], link: 'https://www.notion.so/my-integrations' },
		spotify: { steps: ['Go to developer.spotify.com/dashboard → Create app', 'Get an access token'], link: 'https://developer.spotify.com/dashboard' },
		homeassistant: { steps: ['Open HA → Profile → Long-Lived Access Tokens → Create', 'Copy the token and your HA URL'], link: '' },
		outlook: { steps: ['Register app at portal.azure.com (free, no subscription)', 'Account type: Personal Microsoft accounts only', 'Add Graph permissions: Mail.Read, Mail.Send, Calendars.Read', 'Create client secret, copy ID + secret'], link: 'https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade' },
		flights: { steps: ['Register at developers.amadeus.com (free test env)', 'Create app, copy API Key + Secret'], link: 'https://developers.amadeus.com/' },
		telegram: { steps: ['Message @BotFather on Telegram → /newbot', 'Copy bot token, get chat ID from getUpdates'], link: 'https://t.me/BotFather' },
	};

	function getStatus(item: CatalogEntry): 'connected' | 'available' | 'setup' | 'coming_soon' {
		if (item.coming_soon) return 'coming_soon';
		const key = catalogToKey[item.name] || item.name.toLowerCase();
		if (connectedOAuth.includes(key)) return 'connected';
		if (serviceStatuses[key]) return 'connected';
		if (item.built_in) return 'connected'; // built-in = always active
		return 'available';
	}

	function getStatusLabel(item: CatalogEntry): string {
		const s = getStatus(item);
		if (s === 'connected') return item.built_in ? '✅ Active' : '🟢 Connected';
		if (s === 'coming_soon') return '🔜 Coming soon';
		if (item.requires_oauth) return '🔗 Needs sign-in';
		return '🔧 Setup required';
	}

	function getSetupType(item: CatalogEntry): 'none' | 'oauth' | 'apikey' {
		if (item.built_in || item.coming_soon) return 'none';
		if (item.requires_oauth) return 'oauth';
		if (item.env_vars && item.env_vars.length > 0) return 'apikey';
		return 'none';
	}

	async function connectOAuth(service: string) {
		const provider = service === 'gmail' || service === 'calendar' ? 'google' : service;
		window.location.href = `http://localhost:8001/api/oauth/${provider}/start?service=${service}`;
	}

	async function disconnectOAuth(service: string) {
		await api(`/oauth/connected/${service}`, { method: 'DELETE' });
		connectedOAuth = connectedOAuth.filter(s => s !== service);
	}

	async function disconnectApiKey(service: string) {
		await api(`/service-keys/${service}`, { method: 'DELETE' });
		serviceStatuses = { ...serviceStatuses, [service]: false };
	}

	onMount(async () => {
		try {
			catalog = await api<CatalogEntry[]>('/mcp/catalog');
		} catch {}

		try {
			const conn = await api<{service: string}[]>('/oauth/connected');
			connectedOAuth = conn.map(c => c.service);
		} catch {}

		try {
			const statuses = await api<{service: string; configured: boolean}[]>('/service-keys');
			const s: Record<string, boolean> = {};
			for (const st of statuses) s[st.service] = st.configured;
			serviceStatuses = s;
		} catch {}

		try {
			const agents = await listAgents();
			if (agents.length > 0) defaultAgentId = agents[0].id;
		} catch {}

		loading = false;
	});

	async function handleSlackConfig() {
		if (!slackChannelId.trim() || !defaultAgentId) return;
		slackSaving = true;
		slackSaved = false;
		try {
			await configureSlackWebhook({ slack_channel_id: slackChannelId, agent_id: defaultAgentId });
			slackSaved = true;
			setTimeout(() => slackSaved = false, 3000);
		} catch (e: any) {
			error = e.message;
		} finally {
			slackSaving = false;
		}
	}

	async function handleTelegramConfig() {
		if (!telegramChatId.trim() || !defaultAgentId) return;
		telegramSaving = true;
		telegramSaved = false;
		try {
			await configureTelegramWebhook({ telegram_chat_id: telegramChatId, agent_id: defaultAgentId });
			telegramSaved = true;
			setTimeout(() => telegramSaved = false, 3000);
		} catch (e: any) {
			error = e.message;
		} finally {
			telegramSaving = false;
		}
	}
</script>

<TopNav />

<main class="min-h-dvh pt-14" style="background: var(--bg-app);">
	{#if loading}
		<div class="flex items-center justify-center min-h-[50vh]">
			<div class="stream-dot w-3 h-3 rounded-full" style="background: var(--accent);"></div>
		</div>
	{:else}
		<div class="max-w-3xl mx-auto px-4 md:px-8 py-8">
			<h1 class="text-2xl font-semibold mb-1" style="color: var(--text-primary);">Services</h1>
			<p class="text-sm mb-6" style="color: var(--text-secondary);">Connect services so Motes can help with email, calendar, tasks, and more.</p>

			{#if successMessage}
				<div class="rounded-xl px-4 py-3 mb-6 text-sm" style="background: #10B98120; border: 1px solid #10B98140; color: #10B981;">
					{successMessage}
				</div>
			{/if}
			{#if error}
				<div class="rounded-xl px-4 py-3 mb-6 text-sm" style="background: #EF444420; border: 1px solid #EF444440; color: #EF4444;">
					{error}
				</div>
			{/if}

			<div class="space-y-3">
				{#each catalog as item}
					{@const key = catalogToKey[item.name] || item.name.toLowerCase()}
					{@const status = getStatus(item)}
					{@const setupType = getSetupType(item)}

					<div class="rounded-xl p-4 transition-all duration-150" style="background: var(--bg-card); border: 1px solid var(--border); {status === 'coming_soon' ? 'opacity: 0.5;' : ''}">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3 flex-1 min-w-0">
								<div class="text-sm font-medium" style="color: var(--text-primary);">{item.name}</div>
								{#if item.macos_only}
									<span class="text-xs px-1.5 py-0.5 rounded" style="background: var(--bg-hover); color: var(--text-muted);">macOS</span>
								{/if}
								<span class="text-xs" style="color: {status === 'connected' ? '#10B981' : 'var(--text-muted)'};">{getStatusLabel(item)}</span>
							</div>
							<div class="flex items-center gap-2 flex-shrink-0">
								{#if status === 'connected' && !item.built_in}
									<button
										onclick={() => {
											if (item.requires_oauth) disconnectOAuth(key);
											else disconnectApiKey(key);
										}}
										class="text-xs px-2.5 py-1 rounded-lg transition-colors"
										style="color: #EF4444; border: 1px solid #EF444430;"
									>Disconnect</button>
								{:else if status === 'available' && setupType === 'oauth'}
									<button
										onclick={() => connectOAuth(key)}
										class="text-xs px-3 py-1.5 rounded-lg font-medium text-white"
										style="background: var(--accent);"
									>Connect</button>
								{:else if status === 'available' && setupType === 'apikey'}
									<button
										onclick={() => { configuringService = configuringService === key ? '' : key; keyInputs = {}; }}
										class="text-xs px-3 py-1.5 rounded-lg font-medium text-white"
										style="background: var(--accent);"
									>{configuringService === key ? 'Cancel' : 'Setup'}</button>
								{/if}
							</div>
						</div>
						<p class="text-xs mt-1" style="color: var(--text-secondary);">{item.description}</p>

						<!-- Inline setup form -->
						{#if configuringService === key}
							<div class="mt-3 pt-3" style="border-top: 1px solid var(--border);">
								{#if serviceGuides[key]}
									<div class="mb-3 space-y-1">
										{#each serviceGuides[key].steps as step, i}
											<p class="text-xs" style="color: var(--text-secondary);">{i + 1}. {step}</p>
										{/each}
										{#if serviceGuides[key].link}
											<a href={serviceGuides[key].link} target="_blank" class="text-xs underline" style="color: var(--accent);">Open {item.name} →</a>
										{/if}
									</div>
								{/if}
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
									<button
										onclick={async () => {
											savingKey = true;
											try {
												await api('/service-keys', { method: 'POST', body: JSON.stringify({ service: key, keys: keyInputs }) });
												serviceStatuses = { ...serviceStatuses, [key]: true };
												configuringService = '';
												keyInputs = {};
												successMessage = `✅ ${item.name} connected!`;
												setTimeout(() => { successMessage = ''; }, 4000);
											} catch (e: any) { error = e.message; }
											savingKey = false;
										}}
										disabled={savingKey}
										class="px-3 py-1.5 rounded-lg text-xs font-medium text-white"
										style="background: var(--accent);"
									>{savingKey ? 'Saving...' : 'Save'}</button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Messaging Integrations -->
			<div class="mt-10">
				<h2 class="text-xl font-semibold mb-1" style="color: var(--text-primary);">Messaging Integrations</h2>
				<p class="text-sm mb-6" style="color: var(--text-secondary);">Connect Slack or Telegram so you can message Motes from those platforms.</p>

				<!-- Slack -->
				<div class="rounded-xl p-5 mb-4" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center gap-3 mb-3">
						<span class="text-2xl">💬</span>
						<div>
							<h3 class="text-sm font-semibold" style="color: var(--text-primary);">Slack</h3>
							<p class="text-xs" style="color: var(--text-secondary);">Send messages to Motes from Slack channels</p>
						</div>
					</div>

					<div class="rounded-lg p-3 mb-3" style="background: var(--bg-secondary); border: 1px solid var(--border);">
						<p class="text-xs font-medium mb-2" style="color: var(--text-primary);">Setup Instructions</p>
						<ol class="text-xs space-y-1" style="color: var(--text-secondary);">
							<li>1. Go to <a href="https://api.slack.com/apps" target="_blank" class="underline" style="color: var(--accent);">api.slack.com/apps</a> → Create New App → From Scratch</li>
							<li>2. Under "Event Subscriptions", enable events and set Request URL to:</li>
						</ol>
						<div class="mt-2 flex items-center gap-2">
							<code class="text-xs px-2 py-1 rounded flex-1 font-mono" style="background: var(--bg-app); color: #10B981; border: 1px solid var(--border);">{webhookBaseUrl}/slack</code>
							<button
								onclick={() => navigator.clipboard.writeText(`${webhookBaseUrl}/slack`)}
								class="text-xs px-2 py-1 rounded transition-colors"
								style="background: var(--bg-hover); color: var(--text-muted);"
							>📋 Copy</button>
						</div>
						<ol start={3} class="text-xs space-y-1 mt-2" style="color: var(--text-secondary);">
							<li>3. Subscribe to bot events: <code class="px-1 rounded" style="background: var(--bg-app);">message.channels</code>, <code class="px-1 rounded" style="background: var(--bg-app);">app_mention</code></li>
							<li>4. Install the app to your workspace</li>
							<li>5. Enter your Slack channel ID below</li>
						</ol>
					</div>

					<div class="space-y-3">
						<div>
							<label for="slack-channel" class="text-xs block mb-1" style="color: var(--text-muted);">Slack Channel ID</label>
							<input
								id="slack-channel"
								bind:value={slackChannelId}
								placeholder="e.g., C01ABCDEF23"
								class="w-full px-3 py-2 rounded-lg text-sm outline-none"
								style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
							/>
						</div>
						<div class="flex items-center gap-3">
							<button
								onclick={handleSlackConfig}
								disabled={slackSaving || !slackChannelId.trim() || !defaultAgentId}
								class="px-4 py-1.5 rounded-lg text-xs font-medium text-white disabled:opacity-50"
								style="background: var(--accent);"
							>{slackSaving ? 'Saving...' : 'Save Slack Config'}</button>
							{#if slackSaved}
								<span class="text-xs" style="color: #10B981;">✓ Configured!</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Telegram -->
				<div class="rounded-xl p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center gap-3 mb-3">
						<span class="text-2xl">✈️</span>
						<div>
							<h3 class="text-sm font-semibold" style="color: var(--text-primary);">Telegram</h3>
							<p class="text-xs" style="color: var(--text-secondary);">Chat with Motes via Telegram bot</p>
						</div>
					</div>

					<div class="rounded-lg p-3 mb-3" style="background: var(--bg-secondary); border: 1px solid var(--border);">
						<p class="text-xs font-medium mb-2" style="color: var(--text-primary);">Setup Instructions</p>
						<ol class="text-xs space-y-1" style="color: var(--text-secondary);">
							<li>1. Message <a href="https://t.me/BotFather" target="_blank" class="underline" style="color: var(--accent);">@BotFather</a> on Telegram → <code class="px-1 rounded" style="background: var(--bg-app);">/newbot</code></li>
							<li>2. Configure the bot's webhook URL (via BotFather or API):</li>
						</ol>
						<div class="mt-2 flex items-center gap-2">
							<code class="text-xs px-2 py-1 rounded flex-1 font-mono" style="background: var(--bg-app); color: #10B981; border: 1px solid var(--border);">{webhookBaseUrl}/telegram</code>
							<button
								onclick={() => navigator.clipboard.writeText(`${webhookBaseUrl}/telegram`)}
								class="text-xs px-2 py-1 rounded transition-colors"
								style="background: var(--bg-hover); color: var(--text-muted);"
							>📋 Copy</button>
						</div>
						<ol start={3} class="text-xs space-y-1 mt-2" style="color: var(--text-secondary);">
							<li>3. Send a message to the bot, then get your chat ID from <code class="px-1 rounded" style="background: var(--bg-app);">/getUpdates</code></li>
							<li>4. Enter your Telegram chat ID below</li>
						</ol>
					</div>

					<div class="space-y-3">
						<div>
							<label for="telegram-chat" class="text-xs block mb-1" style="color: var(--text-muted);">Telegram Chat ID</label>
							<input
								id="telegram-chat"
								bind:value={telegramChatId}
								placeholder="e.g., 123456789"
								class="w-full px-3 py-2 rounded-lg text-sm outline-none"
								style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
							/>
						</div>
						<div class="flex items-center gap-3">
							<button
								onclick={handleTelegramConfig}
								disabled={telegramSaving || !telegramChatId.trim() || !defaultAgentId}
								class="px-4 py-1.5 rounded-lg text-xs font-medium text-white disabled:opacity-50"
								style="background: var(--accent);"
							>{telegramSaving ? 'Saving...' : 'Save Telegram Config'}</button>
							{#if telegramSaved}
								<span class="text-xs" style="color: #10B981;">✓ Configured!</span>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</main>
