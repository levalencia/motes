<script lang="ts">
	let { onMenu = () => {} }: { onMenu?: () => void } = $props();
</script>

<header class="md:hidden flex items-center justify-between px-4 py-3" style="border-bottom: 1px solid var(--border); background: var(--bg-app);">
	<div class="flex items-center gap-2">
		<img src="/mascot-sm.png" alt="" class="w-6 h-6" />
		<span class="text-base font-semibold" style="color: var(--text-primary);">Motes</span>
	</div>
	<button onclick={onMenu} class="p-1.5 rounded-lg transition-colors" style="color: var(--text-secondary);" aria-label="Menu">
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 12h16M4 18h16"/></svg>
	</button>
</header>
