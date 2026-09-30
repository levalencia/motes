<script lang="ts">
	let {
		value = $bindable(''),
		placeholder = 'Message Motes...',
		disabled = false,
		onSend = () => {},
		onRecord = () => {},
		recording = false,
	}: {
		value?: string;
		placeholder?: string;
		disabled?: boolean;
		onSend?: () => void;
		onRecord?: () => void;
		recording?: boolean;
	} = $props();

	let textarea: HTMLTextAreaElement;

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			if (value.trim()) onSend();
		}
	}

	function autoResize() {
		if (!textarea) return;
		textarea.style.height = 'auto';
		textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
	}

	$effect(() => {
		value;
		// Auto-resize when value changes
		if (textarea) {
			textarea.style.height = 'auto';
			textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
		}
	});
</script>

<div class="w-full max-w-[var(--content-max)] mx-auto px-4 pb-4 md:pb-6">
	<div
		class="flex items-end gap-2 px-4 py-3 rounded-3xl transition-shadow duration-200"
		style="background: var(--bg-composer); border: 1px solid var(--border); box-shadow: var(--shadow-md);"
	>
		<!-- Attachment button -->
		<button
			class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors duration-150 mb-0.5"
			style="color: var(--text-muted);"
			title="Attach"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v16m8-8H4"/></svg>
		</button>

		<!-- Textarea -->
		<textarea
			bind:this={textarea}
			bind:value
			onkeydown={handleKeydown}
			oninput={autoResize}
			{placeholder}
			{disabled}
			rows="1"
			class="flex-1 resize-none bg-transparent outline-none text-[15px] leading-relaxed max-h-[200px] py-1"
			style="color: var(--text-primary);"
		></textarea>

		<!-- Mic button -->
		<button
			onclick={onRecord}
			class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150 mb-0.5"
			class:animate-pulse={recording}
			style="color: {recording ? '#EF4444' : 'var(--text-muted)'};"
			title={recording ? 'Stop recording' : 'Voice input'}
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-14 0m14 0a7 7 0 00-14 0m14 0v1a7 7 0 01-14 0v-1m7 8v4m-4 0h8M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z"/></svg>
		</button>

		<!-- Send button -->
		<button
			onclick={onSend}
			disabled={!value.trim() || disabled}
			class="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 mb-0.5 disabled:opacity-30"
			style="background: {value.trim() ? 'linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple))' : 'var(--bg-hover)'}; color: white;"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7"/></svg>
		</button>
	</div>
</div>
