<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { clearAuth, username } from '$lib/stores/auth';
	import { theme, toggleTheme } from '$lib/stores/theme';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	interface ConvItem { id: string; title: string; conversation_type: string; updated_at?: string; }

	let { agents = [], conversations = [], onNewChat = () => {}, onRename = (_id: string, _title: string) => {}, onDelete = (_id: string) => {} }: {
		agents?: { id: string; name: string }[];
		conversations?: ConvItem[];
		onNewChat?: () => void;
		onRename?: (id: string, title: string) => void;
		onDelete?: (id: string) => void;
	} = $props();

	const currentPath = $derived($page.url.pathname);
	let editingId = $state('');
	let editTitle = $state('');
	let sidebarAgents = $state<{id: string; name: string}[]>([]);

	const allAgents = $derived(agents.length > 0 ? agents : sidebarAgents);
	const chats = $derived(conversations.filter(c => c.conversation_type === 'chat'));
	const calls = $derived(conversations.filter(c => c.conversation_type === 'call'));
	const defaultAgentId = $derived(allAgents.length > 0 ? allAgents[0].id : '');

	onMount(async () => {
		// If no agents passed as props, fetch them
		if (agents.length === 0) {
			try {
				sidebarAgents = await api<{id: string; name: string}[]>('/agents');
			} catch { /* ignore */ }
		}
	});

	function isActive(path: string): boolean {
		return currentPath === path || currentPath.startsWith(path + '/');
	}

	function startRename(conv: ConvItem) {
		editingId = conv.id;
		editTitle = conv.title;
	}

	function finishRename() {
		if (editingId && editTitle.trim()) {
			onRename(editingId, editTitle.trim());
		}
		editingId = '';
	}

	function logout() {
		clearAuth();
		goto('/login');
	}
</script>

<aside class="fixed left-0 top-0 bottom-0 flex flex-col" style="width: var(--sidebar-width); background: var(--bg-sidebar); border-right: 1px solid var(--border);">
	<!-- Logo -->
	<div class="px-5 pt-5 pb-3 flex items-center gap-2.5">
		<img src="/mascot-sm.png" alt="" class="w-7 h-7" />
		<span class="text-lg font-semibold" style="color: var(--text-primary);">Motes</span>
	</div>

	<!-- New Chat + Call buttons -->
	<div class="px-3 pb-2 space-y-1.5">
		<button
			onclick={onNewChat}
			class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 hover:scale-[1.01]"
			style="background: var(--accent); color: white;"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
			New chat
		</button>
		{#if defaultAgentId}
			<a
				href="/call/{defaultAgentId}"
				class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 hover:scale-[1.01]"
				style="background: #10B981; color: white;"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
				Call Motes
			</a>
		{/if}
	</div>

	<!-- Navigation -->
	<nav class="flex-1 px-3 py-1 space-y-0.5 overflow-y-auto">
		<a href="/dashboard" class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-150"
			style="background: {isActive('/dashboard') ? 'var(--bg-active)' : 'transparent'}; color: {isActive('/dashboard') ? 'var(--accent)' : 'var(--text-secondary)'};">
			<svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
			Dashboard
		</a>
		<a href="/services" class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-150"
			style="background: {isActive('/services') ? 'var(--bg-active)' : 'transparent'}; color: {isActive('/services') ? 'var(--accent)' : 'var(--text-secondary)'};">
			<svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
			Services
		</a>
		<a href="/providers" class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-150"
			style="background: {isActive('/providers') ? 'var(--bg-active)' : 'transparent'}; color: {isActive('/providers') ? 'var(--accent)' : 'var(--text-secondary)'};">
			<svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>
			Providers
		</a>
		<a href="/settings" class="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-150"
			style="background: {isActive('/settings') ? 'var(--bg-active)' : 'transparent'}; color: {isActive('/settings') ? 'var(--accent)' : 'var(--text-secondary)'};">
			<svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
			Settings
		</a>

		<!-- Chat History -->
		{#if chats.length > 0}
			<div class="pt-4 pb-1 px-3">
				<span class="text-xs font-medium uppercase tracking-wider" style="color: var(--text-muted);">💬 Chats</span>
			</div>
			{#each chats.slice(0, 15) as conv}
				{#if editingId === conv.id}
					<div class="px-3 py-1">
						<input
							bind:value={editTitle}
							onblur={finishRename}
							onkeydown={(e) => { if (e.key === 'Enter') finishRename(); if (e.key === 'Escape') { editingId = ''; } }}
							class="w-full text-sm px-2 py-1 rounded-lg outline-none"
							style="background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--accent);"
						/>
					</div>
				{:else}
					<a
						href="/chat/{defaultAgentId}?conversation={conv.id}"
						class="group flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm transition-all duration-150 truncate"
						style="background: {currentPath.includes(conv.id) ? 'var(--bg-active)' : 'transparent'}; color: {currentPath.includes(conv.id) ? 'var(--accent)' : 'var(--text-secondary)'};"
					>
						<span class="truncate flex-1">{conv.title}</span>
						<button
							onclick={(e) => { e.preventDefault(); e.stopPropagation(); startRename(conv); }}
							class="opacity-0 group-hover:opacity-50 hover:!opacity-100 text-xs transition-opacity"
							title="Rename"
						>✏️</button>
						<button
							onclick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(conv.id); }}
							class="opacity-0 group-hover:opacity-50 hover:!opacity-100 text-xs transition-opacity"
							title="Delete"
						>🗑️</button>
					</a>
				{/if}
			{/each}
		{/if}

		<!-- Call History -->
		{#if calls.length > 0}
			<div class="pt-4 pb-1 px-3">
				<span class="text-xs font-medium uppercase tracking-wider" style="color: var(--text-muted);">📞 Calls</span>
			</div>
			{#each calls.slice(0, 10) as conv}
				{#if editingId === conv.id}
					<div class="px-3 py-1">
						<input
							bind:value={editTitle}
							onblur={finishRename}
							onkeydown={(e) => { if (e.key === 'Enter') finishRename(); if (e.key === 'Escape') { editingId = ''; } }}
							class="w-full text-sm px-2 py-1 rounded-lg outline-none"
							style="background: var(--bg-hover); color: var(--text-primary); border: 1px solid var(--accent);"
						/>
					</div>
				{:else}
					<a
						href="/call/{defaultAgentId}?conversation={conv.id}"
						class="group flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm transition-all duration-150 truncate"
						style="background: {currentPath.includes(conv.id) ? 'var(--bg-active)' : 'transparent'}; color: {currentPath.includes(conv.id) ? 'var(--accent)' : 'var(--text-secondary)'};"
					>
						<span class="truncate flex-1">{conv.title}</span>
						<button
							onclick={(e) => { e.preventDefault(); e.stopPropagation(); startRename(conv); }}
							class="opacity-0 group-hover:opacity-50 hover:!opacity-100 text-xs transition-opacity"
							title="Rename"
						>✏️</button>
						<button
							onclick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(conv.id); }}
							class="opacity-0 group-hover:opacity-50 hover:!opacity-100 text-xs transition-opacity"
							title="Delete"
						>🗑️</button>
					</a>
				{/if}
			{/each}
		{/if}
	</nav>

	<!-- Bottom: theme + user -->
	<div class="px-3 py-3 space-y-2" style="border-top: 1px solid var(--border);">
		<div class="flex items-center justify-center px-3">
			<button onclick={toggleTheme} class="text-sm transition-opacity hover:opacity-70" style="color: var(--text-muted);">
				{$theme === 'dark' ? '☀️' : '🌙'}
			</button>
		</div>
		<div class="flex items-center gap-2.5 px-3 py-2 rounded-xl cursor-pointer transition-colors duration-150" style="background: transparent;" onmouseenter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'} onmouseleave={(e) => e.currentTarget.style.background = 'transparent'}>
			<div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white" style="background: linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple));">
				{($username || 'U').charAt(0).toUpperCase()}
			</div>
			<div class="flex-1 min-w-0">
				<div class="text-sm font-medium truncate" style="color: var(--text-primary);">{$username || 'User'}</div>
			</div>
			<button onclick={logout} class="text-xs transition-opacity hover:opacity-70" style="color: var(--text-muted);">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
			</button>
		</div>
	</div>
</aside>
