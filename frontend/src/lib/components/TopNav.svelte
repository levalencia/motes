<script lang="ts">
	import { goto } from '$app/navigation';
	import { clearAuth, username } from '$lib/stores/auth';
	import { theme, toggleTheme } from '$lib/stores/theme';

	let {
		agentId = '',
		agentName = 'Motes',
		onClearThread = () => {},
		clearing = false,
	}: {
		agentId?: string;
		agentName?: string;
		onClearThread?: () => void;
		clearing?: boolean;
	} = $props();

	let showUserMenu = $state(false);

	function logout() {
		clearAuth();
		goto('/login');
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<nav class="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-6 h-14" style="background: var(--bg-app); border-bottom: 1px solid var(--border); backdrop-filter: blur(12px);">
	<!-- Left: Logo -->
	<div class="flex items-center gap-2.5">
		<a href="/dashboard" class="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
			<img src="/mascot-sm.png" alt="" class="w-7 h-7" />
			<span class="text-lg font-semibold" style="color: var(--text-primary);">Motes</span>
		</a>
	</div>

	<!-- Right: Actions -->
	<div class="flex items-center gap-2">
		<!-- Clear thread button -->
		<button
			onclick={onClearThread}
			disabled={clearing}
			class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:opacity-80 disabled:opacity-40"
			style="color: var(--text-muted);"
			title="Clear thread"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
			<span class="hidden md:inline">{clearing ? 'Clearing...' : 'Clear'}</span>
		</button>

		<!-- Call button -->
		{#if agentId}
			<a
				href="/call/{agentId}"
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all hover:scale-105"
				style="background: #10B981; color: white;"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
				<span class="hidden md:inline">Call</span>
			</a>
		{/if}

		<!-- Services -->
		<a
			href="/services"
			class="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
			style="color: var(--text-muted);"
			title="Connected services"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
		</a>

		<!-- Settings -->
		<a
			href="/settings"
			class="flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
			style="color: var(--text-muted);"
			title="Settings"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
		</a>

		<!-- Theme toggle -->
		<button onclick={toggleTheme} class="flex items-center justify-center w-8 h-8 rounded-lg transition-colors" style="color: var(--text-muted);" title="Toggle theme">
			{$theme === 'dark' ? '☀️' : '🌙'}
		</button>

		<!-- User avatar -->
		<div class="relative">
			<button
				onclick={() => { showUserMenu = !showUserMenu; }}
				class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple));"
			>
				{($username || 'U').charAt(0).toUpperCase()}
			</button>
			{#if showUserMenu}
				<div
					class="absolute right-0 top-full mt-1 w-40 rounded-xl overflow-hidden shadow-lg"
					style="background: var(--bg-card); border: 1px solid var(--border);"
				>
					<div class="px-3 py-2 text-sm" style="color: var(--text-primary); border-bottom: 1px solid var(--border);">
						{$username || 'User'}
					</div>
					<button
						onclick={logout}
						class="w-full text-left px-3 py-2 text-sm transition-colors"
						style="color: var(--text-secondary);"
					>
						Sign out
					</button>
				</div>
			{/if}
		</div>
	</div>
</nav>

<!-- Click-away to close user menu -->
{#if showUserMenu}
	<div class="fixed inset-0 z-40" onclick={() => { showUserMenu = false; }}></div>
{/if}
