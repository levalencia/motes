<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	const agentId = $derived($page.params.agentId);

	// Configure marked for clean output
	marked.setOptions({ breaks: true, gfm: true });

	function renderMarkdown(text: string): string {
		const raw = marked.parse(text) as string;
		return DOMPurify.sanitize(raw);
	}

	interface ChatMessage {
		role: 'user' | 'assistant' | 'tool';
		content: string;
		tool_name?: string;
	}

	let messages = $state<ChatMessage[]>([]);
	let input = $state('');
	let streaming = $state(false);
	let conversationId = $state<string | null>(null);
	let agentName = $state('Agent');
	let error = $state('');

	// Voice state
	let recording = $state(false);
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];
	let playingTTS = $state<string | null>(null);
	let hasVoiceProvider = $state(false);
	let voiceProviderId = $state('');

	onMount(async () => {
		try {
			const token = localStorage.getItem('motes_token');
			if (!token) { goto('/login'); return; }

			// Load agents
			const res = await fetch(`http://localhost:8001/api/agents`, {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (!res.ok) { goto('/login'); return; }
			const agents = await res.json();
			const agent = agents.find((a: any) => a.id === agentId);
			if (agent) agentName = agent.name;

			// Check for voice providers
			const vpRes = await fetch(`http://localhost:8001/api/voice/providers`, {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (vpRes.ok) {
				const vps = await vpRes.json();
				if (vps.length > 0) {
					hasVoiceProvider = true;
					voiceProviderId = vps[0].id;
				}
			}
		} catch {
			goto('/login');
		}
	});

	async function startRecording() {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			audioChunks = [];
			mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
			mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
			mediaRecorder.onstop = async () => {
				stream.getTracks().forEach(t => t.stop());
				const blob = new Blob(audioChunks, { type: 'audio/webm' });
				await transcribeAndSend(blob);
			};
			mediaRecorder.start();
			recording = true;
		} catch (e: any) {
			error = 'Microphone access denied: ' + e.message;
		}
	}

	function stopRecording() {
		if (mediaRecorder && recording) {
			mediaRecorder.stop();
			recording = false;
		}
	}

	async function transcribeAndSend(blob: Blob) {
		if (!hasVoiceProvider) {
			// No voice provider — use browser's speech recognition as fallback info
			error = 'No voice provider configured. Add one in Settings → Voice.';
			return;
		}
		const token = localStorage.getItem('motes_token');
		const formData = new FormData();
		formData.append('file', blob, 'audio.webm');

		try {
			const res = await fetch(
				`http://localhost:8001/api/voice/stt?voice_provider_id=${voiceProviderId}`,
				{
					method: 'POST',
					headers: { Authorization: `Bearer ${token}` },
					body: formData,
				}
			);
			if (res.ok) {
				const data = await res.json();
				if (data.text) {
					input = data.text;
					// Auto-send after transcription
					sendMessage();
				}
			} else {
				error = 'Transcription failed';
			}
		} catch {
			error = 'Voice transcription error';
		}
	}

	async function playTTS(text: string, msgId: string) {
		if (playingTTS === msgId) {
			playingTTS = null;
			return;
		}
		playingTTS = msgId;
		const token = localStorage.getItem('motes_token');
		try {
			const body: any = { text: text.slice(0, 4096) };
			if (voiceProviderId) body.voice_provider_id = voiceProviderId;
			// No voice_provider_id = Edge TTS (free, no setup needed)

			const res = await fetch('http://localhost:8001/api/voice/tts', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(body),
			});
			if (res.ok) {
				const audioBlob = await res.blob();
				const url = URL.createObjectURL(audioBlob);
				const audio = new Audio(url);
				audio.onended = () => { playingTTS = null; URL.revokeObjectURL(url); };
				audio.play();
			} else {
				error = 'TTS failed';
				playingTTS = null;
			}
		} catch {
			error = 'TTS error';
			playingTTS = null;
		}
	}

	async function sendMessage() {
		if (!input.trim() || streaming) return;
		const text = input.trim();
		input = '';
		error = '';

		messages = [...messages, { role: 'user', content: text }];
		streaming = true;

		// Add empty assistant message that we'll stream into
		let assistantContent = '';
		messages = [...messages, { role: 'assistant', content: '' }];

		try {
			const token = localStorage.getItem('motes_token');
			const res = await fetch(`http://localhost:8001/api/agents/${agentId}/chat`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`,
				},
				body: JSON.stringify({
					message: text,
					conversation_id: conversationId,
				}),
			});

			if (!res.ok) {
				const body = await res.json().catch(() => ({ detail: 'Unknown error' }));
				throw new Error(body.detail);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						try {
							const event = JSON.parse(line.slice(6));

							if (event.type === 'token') {
								assistantContent += event.content;
								messages = [
									...messages.slice(0, -1),
									{ role: 'assistant', content: assistantContent }
								];
							} else if (event.type === 'tool_call') {
								messages = [
									...messages,
									{ role: 'tool', content: `Calling ${event.name}...`, tool_name: event.name }
								];
							} else if (event.type === 'tool_result') {
								messages = [
									...messages.slice(0, -1),
									{ role: 'tool', content: event.result, tool_name: event.name }
								];
							} else if (event.type === 'done') {
								if (event.conversation_id) {
									conversationId = event.conversation_id;
								}
							} else if (event.type === 'error') {
								error = event.message;
							}
						} catch {
							// skip malformed JSON
						}
					}
				}
			}
		} catch (e: any) {
			error = e.message;
			// Remove empty assistant message on error
			if (messages[messages.length - 1]?.content === '') {
				messages = messages.slice(0, -1);
			}
		} finally {
			streaming = false;
		}
	}
</script>

<div class="min-h-screen bg-gray-950 text-white flex flex-col">
	<!-- Header -->
	<nav class="border-b border-gray-800 px-6 py-3 flex items-center gap-4 shrink-0">
		<a href="/dashboard" class="text-gray-400 hover:text-white">← Back</a>
		<h1 class="text-lg font-semibold">{agentName}</h1>
	</nav>

	<!-- Messages -->
	<div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
		{#if messages.length === 0}
			<div class="flex items-center justify-center h-full">
				<p class="text-gray-500">Start a conversation...</p>
			</div>
		{/if}

		{#each messages as msg}
			<div class="max-w-3xl mx-auto">
				{#if msg.role === 'user'}
					<div class="flex justify-end">
						<div class="bg-blue-600 rounded-lg px-4 py-2 max-w-xl">
							<p class="whitespace-pre-wrap">{msg.content}</p>
						</div>
					</div>
				{:else if msg.role === 'tool'}
					<div class="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm">
						<span class="text-yellow-400 font-mono text-xs">🔧 {msg.tool_name}</span>
						<pre class="text-gray-300 mt-1 whitespace-pre-wrap text-xs">{msg.content}</pre>
					</div>
				{:else}
					<div class="bg-gray-900 border border-gray-800 rounded-lg px-4 py-2 max-w-xl prose prose-invert prose-sm max-w-none">
						<div>{@html renderMarkdown(msg.content)}</div>
						{#if streaming && msg === messages[messages.length - 1]}<span class="animate-pulse">▊</span>{/if}
						{#if !streaming && msg.content}
							<button
								onclick={() => playTTS(msg.content, msg.content.slice(0, 20))}
								class="mt-2 text-xs text-gray-500 hover:text-blue-400 flex items-center gap-1"
								title="Listen to this response"
							>
								{#if playingTTS === msg.content.slice(0, 20)}
									⏹ Stop
								{:else}
									🔊 Listen
								{/if}
							</button>
						{/if}
					</div>
				{/if}
			</div>
		{/each}

		{#if error}
			<div class="max-w-3xl mx-auto">
				<p class="text-red-400 text-sm bg-red-950 border border-red-900 rounded px-4 py-2">{error}</p>
			</div>
		{/if}
	</div>

	<!-- Input -->
	<div class="border-t border-gray-800 px-6 py-4 shrink-0">
		<form onsubmit={(e) => { e.preventDefault(); sendMessage(); }} class="max-w-3xl mx-auto flex gap-3">
			<input
				bind:value={input}
				placeholder="Type a message..."
				disabled={streaming}
				class="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
			/>
			<button
				type="button"
				onclick={() => recording ? stopRecording() : startRecording()}
				disabled={streaming}
				class="px-4 py-3 rounded-lg font-medium {recording ? 'bg-red-600 hover:bg-red-700 animate-pulse' : 'bg-gray-700 hover:bg-gray-600'} disabled:opacity-50"
				title={recording ? 'Stop recording' : 'Voice input'}
			>
				{recording ? '⏹' : '🎤'}
			</button>
			<button
				type="submit"
				disabled={streaming || !input.trim()}
				class="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-medium"
			>
				{streaming ? '...' : 'Send'}
			</button>
		</form>
	</div>
</div>
