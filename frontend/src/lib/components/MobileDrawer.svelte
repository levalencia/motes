<script lang="ts">
	import { goto } from '$app/navigation';
	import { clearAuth, username } from '$lib/stores/auth';
	import { theme, toggleTheme } from '$lib/stores/theme';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	let { open = $bindable(false) }: { open?: boolean } = $props();
	let agentId = $state('');

	const links = [
		{ href: '/dashboard', label: 'Dashboard', icon: '🏠' },
		{ href: '/services', label: 'Services', icon: '🔗' },
		{ href: '/providers', label: 'Providers', icon: '🖥️' },
		{ href: '/settings', label: 'Settings', icon: '⚙️' },
	];

	onMount(async () => {
		try {
			const agents = await api<{id: string}[]>('/agents');
			if (agents.length > 0) agentId = agents[0].id;
		} catch { /* ignore */ }
	});

	function navigate(href: string) {
		open = false;
		goto(href);
	}

	function logout() {
		open = false;
		clearAuth();
		goto('/login');
	}
</script>

{#if open}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 bg-black/40 z-40 md:hidden"
		onclick={() => { open = false; }}
	></div>

	<!-- Drawer -->
	<div class="fixed top-0 left-0 bottom-0 w-72 z-50 flex flex-col md:hidden" style="background: var(--bg-app); box-shadow: var(--shadow-lg);">
		<!-- Header -->
		<div class="flex items-center justify-between px-5 py-4" style="border-bottom: 1px solid var(--border);">
			<div class="flex items-center gap-2">
				<img src="/mascot-sm.png" alt="" class="w-7 h-7" />
				<span class="text-lg font-semibold" style="color: var(--text-primary);">Motes</span>
			</div>
			<button onclick={() => { open = false; }} class="p-1" style="color: var(--text-muted);">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
			</button>
		</div>

		<!-- Links -->
		<nav class="flex-1 px-3 py-3 space-y-1">
			{#if agentId}
				<button
					onclick={() => navigate(`/chat/${agentId}`)}
					class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left font-medium"
					style="background: var(--accent); color: white;"
				>
					<span>💬</span>
					<span>New Chat</span>
				</button>
				<button
					onclick={() => navigate(`/call/${agentId}`)}
					class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left font-medium"
					style="background: #10B981; color: white;"
				>
					<span>📞</span>
					<span>Call Motes</span>
				</button>
			{/if}
			{#each links as link}
				<button
					onclick={() => navigate(link.href)}
					class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left transition-colors"
					style="color: var(--text-secondary);"
				>
					<span>{link.icon}</span>
					<span>{link.label}</span>
				</button>
			{/each}
		</nav>

		<!-- Bottom -->
		<div class="px-4 py-4 space-y-3" style="border-top: 1px solid var(--border);">
			<div class="flex items-center justify-between px-2">
				<button onclick={toggleTheme} style="color: var(--text-muted);">
					{$theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
				</button>
			</div>
			<div class="flex items-center gap-3 px-2">
				<div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white" style="background: linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple));">
					{($username || 'U').charAt(0).toUpperCase()}
				</div>
				<span class="text-sm flex-1" style="color: var(--text-primary);">{$username || 'User'}</span>
				<button onclick={logout} class="text-xs" style="color: var(--text-muted);">Sign out</button>
			</div>
		</div>
	</div>
{/if}
