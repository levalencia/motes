<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	const provider = $derived($page.params.provider);

	let saving = $state(false);
	let clientId = $state('');
	let clientSecret = $state('');
	let error = $state('');
	let alreadyConfigured = $state(false);

	interface Guide {
		title: string;
		icon: string;
		services: string[];
		steps: { title: string; detail: string; link?: string }[];
		redirectUri: string;
		docsUrl: string;
		notes: string[];
	}

	const guides: Record<string, Guide> = {
		google: {
			title: 'Google (Gmail + Calendar)',
			icon: '🔵',
			services: ['Gmail', 'Google Calendar'],
			steps: [
				{
					title: 'Go to Google Cloud Console',
					detail: 'Open the Google Cloud Console and sign in with your Google account.',
					link: 'https://console.cloud.google.com/',
				},
				{
					title: 'Create a project (or select existing)',
					detail:
						'Click the project dropdown at the top → "New Project" → name it "Motes" → Create.',
				},
				{
					title: 'Enable the Gmail and Calendar APIs',
					detail:
						'Go to "APIs & Services" → "Library". Search for "Gmail API" and click Enable. Then search for "Google Calendar API" and click Enable.',
					link: 'https://console.cloud.google.com/apis/library',
				},
				{
					title: 'Configure OAuth consent screen',
					detail:
						'Go to "APIs & Services" → "OAuth consent screen". Choose "External" (or "Internal" if using Google Workspace). Fill in App name: "Motes", your email, and save. Add your email as a test user.',
					link: 'https://console.cloud.google.com/apis/credentials/consent',
				},
				{
					title: 'Create OAuth 2.0 credentials',
					detail:
						'Go to "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID". Application type: "Web application". Name: "Motes".',
					link: 'https://console.cloud.google.com/apis/credentials',
				},
				{
					title: 'Add the redirect URI',
					detail:
						'Under "Authorized redirect URIs", click "Add URI" and paste the redirect URI shown below. Then click Create.',
				},
				{
					title: 'Copy Client ID and Client Secret',
					detail:
						'Google will show your Client ID and Client Secret. Copy both and paste them in the form below.',
				},
			],
			redirectUri: 'http://localhost:8001/api/oauth/callback/google',
			docsUrl: 'https://developers.google.com/identity/protocols/oauth2',
			notes: [
				'While your app is in "Testing" mode, only test users you add can connect.',
				'For production, you\'ll need to submit for Google verification.',
				'One set of credentials works for both Gmail AND Calendar.',
			],
		},
		github: {
			title: 'GitHub',
			icon: '⚫',
			services: ['GitHub (issues, PRs, repos, notifications)'],
			steps: [
				{
					title: 'Go to GitHub Developer Settings',
					detail: 'Open GitHub Settings → Developer settings → OAuth Apps.',
					link: 'https://github.com/settings/developers',
				},
				{
					title: 'Click "New OAuth App"',
					detail: 'Fill in the form with these values:',
				},
				{
					title: 'Set the application details',
					detail:
						'Application name: "Motes"\nHomepage URL: "http://localhost:5173"\nAuthorization callback URL: paste the redirect URI shown below.',
				},
				{
					title: 'Click "Register application"',
					detail: 'GitHub will show your Client ID. Click "Generate a new client secret" to get the secret.',
				},
				{
					title: 'Copy Client ID and Client Secret',
					detail: 'Copy both values and paste them in the form below. The secret is only shown once!',
				},
			],
			redirectUri: 'http://localhost:8001/api/oauth/callback/github',
			docsUrl: 'https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app',
			notes: [
				'GitHub OAuth Apps have no approval process — works immediately.',
				'The token gets repo, read:org, and read:user scopes.',
			],
		},
		slack: {
			title: 'Slack',
			icon: '💜',
			services: ['Slack (messages, channels)'],
			steps: [
				{
					title: 'Go to Slack API',
					detail: 'Open the Slack API site and sign in.',
					link: 'https://api.slack.com/apps',
				},
				{
					title: 'Click "Create New App" → "From scratch"',
					detail: 'Name it "Motes" and select your workspace.',
				},
				{
					title: 'Add OAuth Scopes',
					detail:
						'Go to "OAuth & Permissions" → "Scopes" → "Bot Token Scopes". Add: channels:read, channels:history, chat:write, users:read.',
				},
				{
					title: 'Add the redirect URL',
					detail:
						'Under "OAuth & Permissions" → "Redirect URLs", click "Add New Redirect URL" and paste the URI shown below.',
				},
				{
					title: 'Get credentials from "Basic Information"',
					detail:
						'Go to "Basic Information" → "App Credentials". Copy the Client ID and Client Secret.',
				},
			],
			redirectUri: 'http://localhost:8001/api/oauth/callback/slack',
			docsUrl: 'https://api.slack.com/authentication/oauth-v2',
			notes: [
				'You must be a Slack workspace admin to install the app.',
				'The bot needs to be invited to channels it should access.',
			],
		},
	};

	const guide = $derived(provider ? guides[provider] : undefined);

	onMount(async () => {
		try {
			const apps = await api<{ provider: string }[]>('/oauth/apps');
			alreadyConfigured = apps.some((a) => a.provider === provider);
		} catch {
			goto('/login');
		}
	});

	async function save() {
		if (!clientId.trim() || !clientSecret.trim()) {
			error = 'Both Client ID and Client Secret are required';
			return;
		}
		saving = true;
		error = '';
		try {
			await api('/oauth/apps', {
				method: 'POST',
				body: JSON.stringify({
					provider,
					client_id: clientId,
					client_secret: clientSecret,
				}),
			});
			goto('/services');
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}
</script>

{#if !guide}
	<div class="min-h-screen bg-gray-950 text-white flex items-center justify-center">
		<p>Unknown provider: {provider}</p>
	</div>
{:else}
	<div class="min-h-screen bg-gray-950 text-white">
		<nav class="border-b border-gray-800 px-6 py-4">
			<div class="flex items-center gap-4">
				<a href="/services" class="text-gray-400 hover:text-white">← Services</a>
				<h1 class="text-xl font-bold">Connect {guide.title}</h1>
			</div>
		</nav>

		<main class="max-w-3xl mx-auto px-6 py-8">
			<!-- Header -->
			<div class="flex items-center gap-4 mb-6">
				<div class="w-14 h-14 bg-gray-800 border border-gray-700 rounded-xl flex items-center justify-center text-3xl">
					{guide.icon}
				</div>
				<div>
					<h2 class="text-2xl font-bold">{guide.title}</h2>
					<p class="text-gray-400 text-sm">
						Enables: {guide.services.join(', ')}
					</p>
				</div>
			</div>

			{#if alreadyConfigured}
				<div class="bg-green-950 border border-green-800 rounded-lg px-4 py-3 mb-6 text-sm text-green-400">
					✓ Already configured! Go to <a href="/services" class="underline">Services</a> to connect.
				</div>
			{/if}

			<!-- Step-by-step guide -->
			<div class="mb-8">
				<h3 class="text-lg font-semibold mb-4">Setup Guide</h3>
				<ol class="space-y-4">
					{#each guide.steps as step, i}
						<li class="flex gap-4">
							<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
								{i + 1}
							</div>
							<div class="flex-1 pt-0.5">
								<p class="font-medium">{step.title}</p>
								<p class="text-gray-400 text-sm mt-1 whitespace-pre-line">{step.detail}</p>
								{#if step.link}
									<a
										href={step.link}
										target="_blank"
										rel="noopener"
										class="text-blue-400 text-sm hover:underline mt-1 inline-block"
									>
										Open →
									</a>
								{/if}
							</div>
						</li>
					{/each}
				</ol>
			</div>

			<!-- Redirect URI (copyable) -->
			<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-8">
				<p class="text-sm text-gray-400 mb-2">Redirect URI (copy this into the provider's console):</p>
				<div class="flex items-center gap-2">
					<code class="flex-1 bg-gray-800 px-3 py-2 rounded text-sm text-blue-300 font-mono">
						{guide.redirectUri}
					</code>
					<button
						onclick={() => navigator.clipboard.writeText(guide.redirectUri)}
						class="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
					>
						Copy
					</button>
				</div>
			</div>

			<!-- Credentials form -->
			<div class="bg-gray-900 border border-blue-500/30 rounded-xl p-6 mb-8">
				<h3 class="text-lg font-semibold mb-4">
					{alreadyConfigured ? 'Update' : 'Enter'} Credentials
				</h3>
				<div class="space-y-4">
					<div>
						<label for="client-id" class="block text-sm text-gray-300">Client ID</label>
						<input
							id="client-id"
							bind:value={clientId}
							placeholder="Paste your Client ID here"
							class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
						/>
					</div>
					<div>
						<label for="client-secret" class="block text-sm text-gray-300">Client Secret</label>
						<input
							id="client-secret"
							type="password"
							bind:value={clientSecret}
							placeholder="Paste your Client Secret here"
							class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
						/>
					</div>
				</div>

				{#if error}
					<p class="text-red-400 text-sm mt-3">{error}</p>
				{/if}

				<div class="flex gap-3 mt-5">
					<button
						onclick={save}
						disabled={saving}
						class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
					>
						{saving ? 'Saving...' : 'Save & Go to Services'}
					</button>
					<a
						href="/services"
						class="px-6 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 inline-flex items-center"
					>
						Cancel
					</a>
				</div>
			</div>

			<!-- Notes -->
			{#if guide.notes.length > 0}
				<div class="bg-gray-900/50 border border-gray-800 rounded-xl p-4 mb-8">
					<p class="font-medium text-gray-400 text-sm mb-2">💡 Good to know</p>
					<ul class="space-y-1">
						{#each guide.notes as note}
							<li class="text-gray-500 text-sm">• {note}</li>
						{/each}
					</ul>
				</div>
			{/if}

			<!-- Docs link -->
			<p class="text-center text-gray-600 text-sm">
				Need help? <a href={guide.docsUrl} target="_blank" rel="noopener" class="text-blue-400 hover:underline">Read the official docs →</a>
			</p>
		</main>
	</div>
{/if}
