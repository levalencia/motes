<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { listAgents, api, getThread, clearThread, type Agent, type ThreadMessage } from '$lib/api/client';
	import ChatComposer from '$lib/components/ChatComposer.svelte';
	import StreamingIndicator from '$lib/components/StreamingIndicator.svelte';
	import TopNav from '$lib/components/TopNav.svelte';

	let agentId = $state('');
	let agentName = $state('Motes');
	let messages = $state<ThreadMessage[]>([]);
	let input = $state('');
	let streaming = $state(false);
	let error = $state('');
	let loading = $state(true);
	let recording = $state(false);
	let hasVoiceProvider = $state(false);
	let voiceProviderId = $state('');
	let playingTTS = $state<string | null>(null);
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];
	let messagesEnd: HTMLDivElement;
	let clearing = $state(false);

	function renderMarkdown(text: string): string {
		return DOMPurify.sanitize(marked.parse(text, { async: false }) as string);
	}

	function scrollToBottom() {
		if (messagesEnd) messagesEnd.scrollIntoView({ behavior: 'smooth' });
	}

	$effect(() => {
		messages;
		setTimeout(scrollToBottom, 50);
	});

	onMount(async () => {
		const token = localStorage.getItem('motes_token');
		if (!token) { goto('/login'); return; }

		try {
			const [agents, vpRes] = await Promise.all([
				listAgents(),
				fetch('http://localhost:8001/api/voice/providers', { headers: { Authorization: `Bearer ${token}` } }),
			]);

			if (agents.length === 0) {
				goto('/agents');
				return;
			}

			agentId = agents[0].id;
			agentName = agents[0].name;

			if (vpRes.ok) {
				const vps = await vpRes.json();
				if (vps.length > 0) { hasVoiceProvider = true; voiceProviderId = vps[0].id; }
			}

			// Load thread
			try {
				const thread = await getThread(agentId);
				messages = thread.messages || [];
			} catch {
				messages = [];
			}

			// SSE for proactive notifications
			const es = new EventSource(`http://localhost:8001/api/events/stream?token=${token}`);
			es.addEventListener('notification', (e) => {
				const data = JSON.parse(e.data);
				const newMsg: ThreadMessage = {
					id: crypto.randomUUID(),
					role: 'assistant',
					content: `**${data.title}**\n\n${data.body}`,
					message_type: 'proactive',
					created_at: new Date().toISOString(),
				};
				messages = [...messages, newMsg];
			});
		} catch (err: any) {
			if (err?.message?.includes('401') || err?.message?.includes('auth')) {
				goto('/login');
			}
		} finally {
			loading = false;
		}
	});

	async function sendMessage(text?: string) {
		let msg = text || input;
		if (!msg.trim() || streaming) return;
		input = '';

		// Add user message to display immediately
		const userMsg: ThreadMessage = {
			id: crypto.randomUUID(),
			role: 'user',
			content: msg,
			message_type: 'chat',
			created_at: new Date().toISOString(),
		};
		messages = [...messages, userMsg];
		streaming = true;
		error = '';

		const token = localStorage.getItem('motes_token');
		try {
			const res = await fetch(`http://localhost:8001/api/agents/${agentId}/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
				body: JSON.stringify({ message: msg }),
			});

			if (!res.ok) {
				let detail = `HTTP ${res.status}`;
				try { const b = await res.text(); detail = JSON.parse(b).detail || detail; } catch {}
				throw new Error(detail);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');

			// Add empty assistant message
			const assistantMsg: ThreadMessage = {
				id: crypto.randomUUID(),
				role: 'assistant',
				content: '',
				message_type: 'chat',
				created_at: new Date().toISOString(),
			};
			messages = [...messages, assistantMsg];
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
							const data = JSON.parse(line.slice(6));
							if (data.type === 'token') {
								messages[messages.length - 1].content += data.content;
								messages = [...messages];
							} else if (data.type === 'tool_call') {
								// Insert tool message before the assistant message
								const toolMsg: ThreadMessage = {
									id: crypto.randomUUID(),
									role: 'tool',
									content: data.result || '',
									message_type: 'system',
									created_at: new Date().toISOString(),
								};
								messages = [...messages.slice(0, -1), toolMsg, messages[messages.length - 1]];
							} else if (data.type === 'done') {
								messages[messages.length - 1].content = data.content;
								messages = [...messages];
							}
						} catch {}
					}
				}
			}
		} catch (e: any) {
			error = e.message;
			if (messages[messages.length - 1]?.content === '') messages = messages.slice(0, -1);
		} finally {
			streaming = false;
		}
	}

	async function handleClearThread() {
		if (!agentId || clearing) return;
		clearing = true;
		try {
			await clearThread(agentId);
			messages = [];
		} catch (e: any) {
			error = e.message;
		} finally {
			clearing = false;
		}
	}

	async function startRecording() {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			audioChunks = [];
			mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
			mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
			mediaRecorder.onstop = async () => {
				stream.getTracks().forEach(t => t.stop());
				const blob = new Blob(audioChunks, { type: 'audio/webm' });
				const token = localStorage.getItem('motes_token');
				const formData = new FormData();
				formData.append('file', blob, 'audio.webm');
				let url = 'http://localhost:8001/api/voice/stt';
				if (voiceProviderId) url += `?voice_provider_id=${voiceProviderId}`;
				try {
					const res = await fetch(url, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData });
					if (res.ok) { const data = await res.json(); if (data.text) { input = data.text; sendMessage(); } }
				} catch {}
			};
			mediaRecorder.start();
			recording = true;
		} catch (e: any) { error = 'Microphone denied: ' + e.message; }
	}

	function toggleRecording() {
		if (recording) {
			if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
			recording = false;
		} else {
			startRecording();
		}
	}

	async function playTTS(text: string, id: string) {
		if (playingTTS === id) { playingTTS = null; return; }
		playingTTS = id;
		const token = localStorage.getItem('motes_token');
		try {
			const body: any = { text: text.slice(0, 4096) };
			if (voiceProviderId) body.voice_provider_id = voiceProviderId;
			const res = await fetch('http://localhost:8001/api/voice/tts', {
				method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
			});
			if (res.ok) {
				const blob = await res.blob();
				const url = URL.createObjectURL(blob);
				const audio = new Audio(url);
				audio.onended = () => { playingTTS = null; URL.revokeObjectURL(url); };
				audio.play();
			} else { playingTTS = null; }
		} catch { playingTTS = null; }
	}

	function getMessageStyle(msg: ThreadMessage): { prefix: string; bgClass: string; textClass: string; isSystem: boolean } {
		switch (msg.message_type) {
			case 'call':
				return { prefix: '📞 ', bgClass: 'bg-emerald-900/20 border-emerald-800/30', textClass: '', isSystem: false };
			case 'proactive':
				return { prefix: '💡 ', bgClass: 'bg-amber-900/20 border-amber-800/30', textClass: '', isSystem: false };
			case 'system':
				return { prefix: '', bgClass: '', textClass: '', isSystem: true };
			default:
				return { prefix: '', bgClass: '', textClass: '', isSystem: false };
		}
	}
</script>

<TopNav {agentId} {agentName} onClearThread={handleClearThread} {clearing} />

<!-- Main content area -->
<main class="fixed inset-0 pt-14 flex flex-col" style="background: var(--bg-app);">
	<!-- Messages area -->
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex-1 flex items-center justify-center h-full">
				<div class="stream-dot w-3 h-3 rounded-full" style="background: var(--accent);"></div>
			</div>
		{:else if messages.length === 0}
			<!-- Welcome screen when thread is empty -->
			<div class="flex flex-col items-center justify-center h-full px-4 pb-8">
				<div class="mascot-float mb-4">
					<img src="/mascot.png" alt="Motes" class="w-24 h-24 md:w-32 md:h-32 object-contain drop-shadow-lg" />
				</div>
				<h1 class="text-2xl md:text-3xl font-semibold mb-2" style="color: var(--text-primary);">
					Hi, I'm {agentName}
				</h1>
				<p class="text-center max-w-md mb-6 text-sm" style="color: var(--text-secondary);">
					Your AI assistant. Everything lives in one thread — chats, calls, and proactive insights.
				</p>
				<!-- Suggestion chips -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg">
					{#each [
						{ icon: '📧', text: 'Show me my unread emails' },
						{ icon: '📅', text: "What's on my calendar today?" },
						{ icon: '🔍', text: 'Search the web for AI news' },
						{ icon: '📁', text: 'Find my most recent files' },
					] as s}
						<button
							onclick={() => sendMessage(s.text)}
							class="flex items-center gap-3 px-4 py-3 rounded-2xl text-left text-sm transition-all duration-200 hover:-translate-y-0.5"
							style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
						>
							<span class="text-lg">{s.icon}</span>
							<span>{s.text}</span>
						</button>
					{/each}
				</div>
			</div>
		{:else}
			<div class="max-w-[var(--content-max)] mx-auto px-4 md:px-8 py-6 space-y-4">
				{#each messages as msg, i}
					{@const style = getMessageStyle(msg)}

					{#if style.isSystem}
						<!-- System message (centered, gray, small) -->
						<div class="flex justify-center">
							<div class="text-xs px-3 py-1.5 rounded-full" style="background: var(--bg-secondary); color: var(--text-muted);">
								{msg.content}
							</div>
						</div>
					{:else if msg.role === 'user'}
						<!-- User message -->
						<div class="flex justify-end">
							<div class="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-tr-md text-[15px]" style="background: var(--accent); color: white;">
								{msg.content}
							</div>
						</div>
					{:else if msg.role === 'tool'}
						<!-- Tool result -->
						<div class="flex gap-3">
							<div class="w-6 h-6 flex-shrink-0 mt-0.5 flex items-center justify-center rounded-full" style="background: var(--bg-hover);">
								<span class="text-xs">🔧</span>
							</div>
							<div class="max-w-[85%] px-3 py-2 rounded-xl text-xs" style="background: var(--bg-secondary); border: 1px solid var(--border);">
								<pre class="whitespace-pre-wrap" style="color: var(--text-secondary);">{msg.content}</pre>
							</div>
						</div>
					{:else}
						<!-- Assistant message (chat, call, proactive) -->
						<div class="flex gap-3">
							<img src="/mascot-sm.png" alt="" class="w-6 h-6 flex-shrink-0 mt-0.5" />
							<div class="max-w-[85%]">
								{#if msg.message_type !== 'chat'}
									<div class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-[15px] leading-relaxed {style.bgClass}" style="border: 1px solid; color: var(--text-primary);">
										<span>{style.prefix}</span>
										<div class="chat-prose">
											{@html renderMarkdown(msg.content)}
										</div>
									</div>
								{:else}
									<div class="chat-prose text-[15px] leading-relaxed" style="color: var(--text-primary);">
										{@html renderMarkdown(msg.content)}
										{#if streaming && i === messages.length - 1 && msg.content}
											<StreamingIndicator />
										{/if}
									</div>
								{/if}
								{#if !streaming && msg.content && msg.role === 'assistant'}
									<div class="flex items-center gap-3 mt-2">
										<button
											onclick={() => playTTS(msg.content, msg.id)}
											class="text-xs flex items-center gap-1 transition-opacity hover:opacity-70"
											style="color: var(--text-muted);"
										>
											{playingTTS === msg.id ? '⏹ Stop' : '🔊 Listen'}
										</button>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				{/each}

				{#if streaming && messages[messages.length - 1]?.content === ''}
					<div class="flex gap-3">
						<img src="/mascot-sm.png" alt="" class="w-6 h-6 flex-shrink-0 mt-0.5" />
						<StreamingIndicator />
					</div>
				{/if}

				<div bind:this={messagesEnd}></div>
			</div>
		{/if}
	</div>

	<!-- Error -->
	{#if error}
		<div class="max-w-[var(--content-max)] mx-auto px-4 pb-2 w-full">
			<div class="text-sm px-3 py-2 rounded-lg" style="background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;">
				{error}
				<button onclick={() => { error = ''; }} class="ml-2 text-xs opacity-60 hover:opacity-100">✕</button>
			</div>
		</div>
	{/if}

	<!-- Composer -->
	<ChatComposer
		bind:value={input}
		disabled={streaming}
		onSend={() => sendMessage()}
		onRecord={toggleRecording}
		{recording}
	/>
</main>
