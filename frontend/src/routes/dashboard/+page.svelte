<script lang="ts">
	import { goto } from '$app/navigation';
	import { listAgents, listProviders, api, type Agent, type Provider } from '$lib/api/client';
	import { onMount } from 'svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import MobileHeader from '$lib/components/MobileHeader.svelte';
	import MobileDrawer from '$lib/components/MobileDrawer.svelte';
	import WelcomeScreen from '$lib/components/WelcomeScreen.svelte';
	import ChatComposer from '$lib/components/ChatComposer.svelte';

	let agents = $state<Agent[]>([]);
	let providers = $state<Provider[]>([]);
	let connectedServices = $state(0);
	let unreadCount = $state(0);
	let loading = $state(true);
	let drawerOpen = $state(false);

	onMount(async () => {
		try {
			const [a, p, svc, notif] = await Promise.all([
				listAgents(),
				listProviders(),
				api<{ service: string }[]>('/oauth/connected'),
				api<{ count: number }>('/notifications/unread-count'),
			]);
			agents = a;
			providers = p;
			connectedServices = svc.length;
			unreadCount = notif.count;
		} catch (e: any) {
			if (e?.message?.includes('401')) goto('/login');
		} finally {
			loading = false;
		}
	});

	function handleSend(msg: string) {
		if (agents.length > 0) {
			goto(`/chat/${agents[0].id}`);
		} else {
			goto('/agents');
		}
	}
</script>

<!-- Desktop sidebar -->
<div class="hidden md:block">
	<Sidebar agents={agents.map(a => ({id: a.id, name: a.name}))} onNewChat={() => { if (agents[0]) goto(`/chat/${agents[0].id}`); }} />
</div>

<!-- Mobile -->
<MobileHeader onMenu={() => { drawerOpen = true; }} />
<MobileDrawer bind:open={drawerOpen} />

<!-- Main -->
<main class="flex flex-col md:ml-[var(--sidebar-width)] overflow-hidden md:h-dvh" style="background: var(--bg-app); height: calc(100dvh - 49px);">
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<div class="stream-dot w-3 h-3 rounded-full" style="background: var(--accent);"></div>
		</div>
	{:else}
		<!-- Welcome / Quick stats -->
		<div class="flex-1 flex flex-col">
			<WelcomeScreen onSend={handleSend} />

			<!-- Stats cards (desktop only) -->
			<div class="hidden md:grid max-w-lg mx-auto w-full px-4 pb-8 grid-cols-3 gap-3">
				<a href="/agents" class="px-4 py-3 rounded-2xl text-center transition-all duration-200 hover:-translate-y-0.5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="text-2xl font-semibold" style="color: var(--text-primary);">{agents.length}</div>
					<div class="text-xs mt-0.5" style="color: var(--text-muted);">Agents</div>
				</a>
				<a href="/providers" class="px-4 py-3 rounded-2xl text-center transition-all duration-200 hover:-translate-y-0.5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="text-2xl font-semibold" style="color: var(--text-primary);">{providers.length}</div>
					<div class="text-xs mt-0.5" style="color: var(--text-muted);">Providers</div>
				</a>
				<a href="/services" class="px-4 py-3 rounded-2xl text-center transition-all duration-200 hover:-translate-y-0.5" style="background: var(--bg-card); border: 1px solid var(--border);">
					<div class="text-2xl font-semibold" style="color: var(--text-primary);">{connectedServices}</div>
					<div class="text-xs mt-0.5" style="color: var(--text-muted);">Services</div>
				</a>
			</div>
		</div>

		<!-- Composer (routes to chat) -->
		<ChatComposer placeholder="Message Motes..." onSend={() => handleSend('')} />
	{/if}
</main>
