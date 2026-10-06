<script lang="ts">
	let {
		value = $bindable(''),
		placeholder = 'Message Motes...',
		disabled = false,
		onSend = () => {},
		onRecord = () => {},
		onImageAttach = (_url: string, _filename: string) => {},
		recording = false,
		agentId = '',
	}: {
		value?: string;
		placeholder?: string;
		disabled?: boolean;
		onSend?: () => void;
		onRecord?: () => void;
		onImageAttach?: (url: string, filename: string) => void;
		recording?: boolean;
		agentId?: string;
	} = $props();

	let textarea: HTMLTextAreaElement;
	let fileInput: HTMLInputElement;
	let uploading = $state(false);
	let attachedImage = $state<{ url: string; filename: string } | null>(null);

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			if (value.trim() || attachedImage) onSend();
		}
	}

	function autoResize() {
		if (!textarea) return;
		textarea.style.height = 'auto';
		textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
	}

	async function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		if (!file.type.startsWith('image/')) {
			alert('Only images are supported');
			return;
		}

		uploading = true;
		try {
			const token = localStorage.getItem('motes_token');
			const formData = new FormData();
			formData.append('file', file);

			const res = await fetch(`http://localhost:8001/api/agents/${agentId}/images`, {
				method: 'POST',
				headers: { Authorization: `Bearer ${token}` },
				body: formData,
			});

			if (res.ok) {
				const data = await res.json();
				attachedImage = { url: data.url, filename: data.filename };
				onImageAttach(data.url, data.filename);
			} else {
				alert('Upload failed');
			}
		} catch {
			alert('Upload error');
		} finally {
			uploading = false;
			input.value = '';
		}
	}

	export function clearAttachment() {
		attachedImage = null;
	}

	export function getAttachedImage() {
		return attachedImage;
	}

	$effect(() => {
		value;
		if (textarea) {
			textarea.style.height = 'auto';
			textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
		}
	});
</script>

<div class="w-full max-w-[var(--content-max)] mx-auto px-3 pb-2 md:px-4 md:pb-6" style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom));">
	<!-- Image preview -->
	{#if attachedImage}
		<div class="flex items-center gap-2 mb-2 px-4">
			<div class="relative inline-block">
				<img src="http://localhost:8001{attachedImage.url}" alt="Attached" class="w-16 h-16 rounded-lg object-cover border border-gray-600" />
				<button
					onclick={() => { attachedImage = null; }}
					class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center"
				>✕</button>
			</div>
			<span class="text-xs text-gray-400">{attachedImage.filename}</span>
		</div>
	{/if}

	<div
		class="flex items-end gap-2 px-4 py-3 rounded-3xl transition-shadow duration-200"
		style="background: var(--bg-composer); border: 1px solid var(--border); box-shadow: var(--shadow-md);"
	>
		<!-- Hidden file input -->
		<input
			bind:this={fileInput}
			type="file"
			accept="image/*"
			class="hidden"
			onchange={handleFileSelect}
		/>

		<!-- Attachment button -->
		<button
			onclick={() => fileInput?.click()}
			class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors duration-150 mb-0.5"
			style="color: {uploading ? 'var(--accent)' : 'var(--text-muted)'};"
			title="Attach image"
			disabled={uploading}
		>
			{#if uploading}
				<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
			{:else}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
			{/if}
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
			disabled={(!value.trim() && !attachedImage) || disabled}
			class="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 mb-0.5 disabled:opacity-30"
			style="background: {(value.trim() || attachedImage) ? 'linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple))' : 'var(--bg-hover)'}; color: white;"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7"/></svg>
		</button>
	</div>
</div>
