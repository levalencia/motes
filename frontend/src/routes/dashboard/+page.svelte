<script lang="ts">
	import { goto } from '$app/navigation';
	import { listAgents, listProviders, api, type Agent, type Provider } from '$lib/api/client';
	import { clearAuth, username } from '$lib/stores/auth';
	import { theme, toggleTheme } from '$lib/stores/theme';
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

<div class="min-h-screen transition-colors duration-200" style="background: var(--bg-primary); color: var(--text-primary);">
	<!-- Top nav -->
	<nav class="px-6 py-4 flex justify-between items-center" style="border-bottom: 1px solid var(--border);">
		<div class="flex items-center gap-3">
			<img src="/logo.png" alt="Motes" class="h-8" />
		</div>
		<div class="flex items-center gap-4">
			<a href="/providers" class="text-sm hover:opacity-100 opacity-60 transition-opacity" style="color: var(--text-secondary);">Providers</a>
			<a href="/agents" class="text-sm hover:opacity-100 opacity-60 transition-opacity" style="color: var(--text-secondary);">Agents</a>
			<a href="/services" class="text-sm hover:opacity-100 opacity-60 transition-opacity" style="color: var(--text-secondary);">Services</a>
			<a href="/settings" class="text-sm hover:opacity-100 opacity-60 transition-opacity" style="color: var(--text-secondary);">Settings</a>
			<span style="color: var(--border);">|</span>
			<!-- Theme toggle -->
			<button
				onclick={toggleTheme}
				class="text-lg hover:opacity-80 transition-opacity"
				title="Toggle dark/light theme"
			>
				{$theme === 'dark' ? '☀️' : '🌙'}
			</button>
			<span class="text-sm" style="color: var(--text-secondary);">{$username}</span>
			<button onclick={() => { clearAuth(); goto('/login'); }} class="text-sm hover:opacity-100 opacity-60" style="color: var(--text-muted);">
				Sign out
			</button>
		</div>
	</nav>

	<main class="max-w-6xl mx-auto px-6 py-8">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div style="color: var(--text-muted);">Loading...</div>
			</div>
		{:else}
			<!-- Stats row -->
			<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
				<div class="rounded-xl p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center justify-between">
						<span class="text-xs uppercase tracking-wider" style="color: var(--text-muted);">Agents</span>
						<span class="text-2xl">🤖</span>
					</div>
					<p class="text-3xl font-bold mt-1">{agents.length}</p>
					<a href="/agents" class="text-xs mt-2 inline-block hover:underline" style="color: var(--motes-blue, #4D5BF9);">Manage →</a>
				</div>
				<div class="rounded-xl p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center justify-between">
						<span class="text-xs uppercase tracking-wider" style="color: var(--text-muted);">Providers</span>
						<span class="text-2xl">⚡</span>
					</div>
					<p class="text-3xl font-bold mt-1">{providers.length}</p>
					<a href="/providers" class="text-xs mt-2 inline-block hover:underline" style="color: var(--motes-blue, #4D5BF9);">Manage →</a>
				</div>
				<div class="rounded-xl p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center justify-between">
						<span class="text-xs uppercase tracking-wider" style="color: var(--text-muted);">Services</span>
						<span class="text-2xl">🔌</span>
					</div>
					<p class="text-3xl font-bold mt-1">{connectedServices}</p>
					<a href="/services" class="text-xs mt-2 inline-block hover:underline" style="color: var(--motes-blue, #4D5BF9);">Connect →</a>
				</div>
				<div class="rounded-xl p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="flex items-center justify-between">
						<span class="text-xs uppercase tracking-wider" style="color: var(--text-muted);">Status</span>
						<span class="text-2xl">🟢</span>
					</div>
					<p class="text-xl font-bold mt-1" style="color: var(--motes-teal, #2DD4A8);">All systems online</p>
				</div>
			</div>

			<!-- Agents section -->
			<div class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold">Your Agents</h2>
					<a href="/agents" class="text-sm hover:underline" style="color: var(--motes-blue, #4D5BF9);">+ Create Agent</a>
				</div>

				{#if agents.length === 0}
					<div class="rounded-xl p-12 text-center" style="background: var(--bg-card); border: 1px dashed var(--border);">
						<p class="text-4xl mb-3">🤖</p>
						<p class="font-medium" style="color: var(--text-secondary);">No agents yet</p>
						<p class="text-sm mt-1" style="color: var(--text-muted);">
							{#if providers.length === 0}
								<a href="/providers" class="hover:underline" style="color: var(--motes-blue);">Add a provider</a> first, then create an agent.
							{:else}
								<a href="/agents" class="hover:underline" style="color: var(--motes-blue);">Create your first agent</a> to get started.
							{/if}
						</p>
					</div>
				{:else}
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
						{#each agents as agent}
							<a
								href="/chat/{agent.id}"
								class="rounded-xl p-5 transition-all group"
								style="background: var(--bg-card); border: 1px solid var(--border);"
								onmouseenter={(e) => e.currentTarget.style.borderColor = 'var(--motes-blue)'}
								onmouseleave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
							>
								<div class="flex items-start gap-3">
									<div class="w-10 h-10 rounded-full flex items-center justify-center text-lg flex-shrink-0 text-white" style="background: linear-gradient(135deg, var(--motes-blue), var(--motes-purple));">
										{agent.name[0]}
									</div>
									<div class="flex-1 min-w-0">
										<h3 class="font-semibold">{agent.name}</h3>
										<p class="text-xs mt-0.5" style="color: var(--text-muted);">{agent.model || 'Unknown model'}</p>
									</div>
									<div class="w-2 h-2 rounded-full mt-2 flex-shrink-0" style="background: var(--motes-teal);" title="Online"></div>
								</div>
								<p class="text-xs mt-3 line-clamp-2" style="color: var(--text-muted);">{agent.system_prompt}</p>
								<div class="flex items-center gap-3 mt-3 text-xs" style="color: var(--text-muted);">
									<span>💬 Chat</span>
									<span>🧠 Memory</span>
									<span>🔧 Tools</span>
									<span>🎤 Voice</span>
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
					<a href="/services" class="rounded-xl p-5 transition-all" style="background: var(--bg-card); border: 1px solid var(--border);"
						onmouseenter={(e) => e.currentTarget.style.borderColor = 'var(--border-hover)'}
						onmouseleave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
					>
						<p class="text-2xl mb-2">📧</p>
						<h3 class="font-medium">Connect Gmail</h3>
						<p class="text-xs mt-1" style="color: var(--text-muted);">Let your agents read and send emails</p>
					</a>
					<a href="/services" class="rounded-xl p-5 transition-all" style="background: var(--bg-card); border: 1px solid var(--border);"
						onmouseenter={(e) => e.currentTarget.style.borderColor = 'var(--border-hover)'}
						onmouseleave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
					>
						<p class="text-2xl mb-2">📅</p>
						<h3 class="font-medium">Connect Calendar</h3>
						<p class="text-xs mt-1" style="color: var(--text-muted);">Schedule meetings and check availability</p>
					</a>
					<a href="/services" class="rounded-xl p-5 transition-all" style="background: var(--bg-card); border: 1px solid var(--border);"
						onmouseenter={(e) => e.currentTarget.style.borderColor = 'var(--border-hover)'}
						onmouseleave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
					>
						<p class="text-2xl mb-2">📁</p>
						<h3 class="font-medium">Access Files</h3>
						<p class="text-xs mt-1" style="color: var(--text-muted);">Browse and edit files on your computer</p>
					</a>
				</div>
			</div>
		{/if}
	</main>
</div>
