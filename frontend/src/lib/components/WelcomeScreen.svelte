<script lang="ts">
	let { onSend = (_msg: string) => {} }: { onSend?: (msg: string) => void } = $props();

	const suggestions = [
		{ icon: '📧', text: 'Show me my unread emails', color: '#4F5BD5' },
		{ icon: '📅', text: "What's on my calendar today?", color: '#7B4FBF' },
		{ icon: '🔍', text: 'Search the web for AI news', color: '#38A1F3' },
		{ icon: '📁', text: 'Find my most recent files', color: '#2DD4A8' },
	];
</script>

<div class="flex flex-col items-center justify-center flex-1 px-4 pb-2 md:pb-8 min-h-0">
	<!-- Mascot -->
	<div class="mascot-float mb-3 md:mb-6">
		<img src="/mascot.png" alt="Motes" class="w-20 h-20 md:w-36 md:h-36 object-contain drop-shadow-lg" />
	</div>

	<!-- Title -->
	<h1 class="text-2xl md:text-4xl font-semibold mb-1 md:mb-2" style="color: var(--text-primary);">
		Hi, I'm Motes
	</h1>
	<p class="text-center max-w-md mb-4 md:mb-8 text-xs md:text-[15px]" style="color: var(--text-secondary); line-height: 1.6;">
		Your AI assistant for deeper thinking, faster answers and bigger ideas.
	</p>

	<!-- Suggestion cards — horizontal scroll on mobile, 2x2 grid on desktop -->
	<div class="hidden md:grid grid-cols-2 gap-3 w-full max-w-lg">
		{#each suggestions as s}
			<button
				onclick={() => onSend(s.text)}
				class="group flex items-center gap-3 px-4 py-3.5 rounded-2xl text-left text-sm transition-all duration-200 hover:-translate-y-0.5"
				style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
				onmouseenter={(e) => { e.currentTarget.style.borderColor = s.color + '40'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}
				onmouseleave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
			>
				<span class="text-lg flex-shrink-0">{s.icon}</span>
				<span class="flex-1">{s.text}</span>
				<svg class="w-4 h-4 opacity-0 group-hover:opacity-50 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
			</button>
		{/each}
	</div>
	<!-- Mobile: horizontal scroll chips -->
	<div class="flex md:hidden gap-2 w-full overflow-x-auto pb-2 px-1 -mx-1" style="scrollbar-width: none; -webkit-overflow-scrolling: touch;">
		{#each suggestions as s}
			<button
				onclick={() => onSend(s.text)}
				class="flex items-center gap-2 px-3 py-2 rounded-xl text-xs whitespace-nowrap flex-shrink-0"
				style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
			>
				<span>{s.icon}</span>
				<span>{s.text}</span>
			</button>
		{/each}
	</div>
</div>
