<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import MobileHeader from '$lib/components/MobileHeader.svelte';
	import MobileDrawer from '$lib/components/MobileDrawer.svelte';
	import WelcomeScreen from '$lib/components/WelcomeScreen.svelte';
	import ChatComposer from '$lib/components/ChatComposer.svelte';
	import StreamingIndicator from '$lib/components/StreamingIndicator.svelte';

	const agentId = $derived($page.params.agentId);

	interface ChatMessage {
		role: string;
		content: string;
		tool_name?: string;
		tool_call_id?: string;
	}

	let messages = $state<ChatMessage[]>([]);
	let input = $state('');
	let streaming = $state(false);
	let conversationId = $state<string | null>(null);
	let agentName = $state('Agent');
	let agents = $state<{id: string; name: string}[]>([]);
	let error = $state('');
	let recording = $state(false);
	let drawerOpen = $state(false);
	let unreadCount = $state(0);
	let lastProactiveNotification = $state('');
	let hasVoiceProvider = $state(false);
	let voiceProviderId = $state('');
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];
	let messagesEnd: HTMLDivElement;
	let playingTTS = $state<string | null>(null);

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
			const [agentsRes, vpRes, notifRes] = await Promise.all([
				fetch('http://localhost:8001/api/agents', { headers: { Authorization: `Bearer ${token}` } }),
				fetch('http://localhost:8001/api/voice/providers', { headers: { Authorization: `Bearer ${token}` } }),
				fetch('http://localhost:8001/api/notifications/unread-count', { headers: { Authorization: `Bearer ${token}` } }),
			]);

			if (!agentsRes.ok) { goto('/login'); return; }
			agents = await agentsRes.json();
			const agent = agents.find((a: any) => a.id === agentId);
			if (agent) agentName = agent.name;

			if (vpRes.ok) {
				const vps = await vpRes.json();
				if (vps.length > 0) { hasVoiceProvider = true; voiceProviderId = vps[0].id; }
			}
			if (notifRes.ok) {
				unreadCount = (await notifRes.json()).count;
			}

			// SSE for proactive notifications
			const es = new EventSource(`http://localhost:8001/api/events/stream?token=${token}`);
			es.addEventListener('notification', (e) => {
				const data = JSON.parse(e.data);
				const notifText = `💡 **${data.title}**\n\n${data.body}`;
				messages = [...messages, { role: 'assistant', content: notifText }];
				// Store last notification so agent can reference it
				lastProactiveNotification = notifText;
			});
		} catch { goto('/login'); }
	});

	async function sendMessage(text?: string) {
		let msg = text || input;
		if (!msg.trim() || streaming) return;
		input = '';

		// If there's a recent proactive notification, inject context
		if (lastProactiveNotification) {
			msg = `[Context: Motes just proactively notified me: "${lastProactiveNotification}"]\n\n${msg}`;
			lastProactiveNotification = '';
		}

		messages = [...messages, { role: 'user', content: text || msg.split('\n\n').pop() || msg }];
		streaming = true;
		error = '';

		const token = localStorage.getItem('motes_token');
		try {
			const res = await fetch(`http://localhost:8001/api/agents/${agentId}/chat`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
				body: JSON.stringify({ message: msg, conversation_id: conversationId }),
			});

			if (!res.ok) {
				let detail = `HTTP ${res.status}`;
				try { const b = await res.text(); detail = JSON.parse(b).detail || detail; } catch {}
				throw new Error(detail);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error('No response body');

			messages = [...messages, { role: 'assistant', content: '' }];
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
								messages = [...messages.slice(0, -1), { role: 'tool', content: data.result || '', tool_name: data.tool }, messages[messages.length - 1]];
							} else if (data.type === 'done') {
								messages[messages.length - 1].content = data.content;
								messages = [...messages];
								if (data.conversation_id) conversationId = data.conversation_id;
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
</script>

<!-- Desktop sidebar (hidden on mobile) -->
<div class="hidden md:block">
	<Sidebar {agents} onNewChat={() => { messages = []; conversationId = null; }} />
</div>

<!-- Mobile header + drawer -->
<MobileHeader onMenu={() => { drawerOpen = true; }} />
<MobileDrawer bind:open={drawerOpen} />

<!-- Main content -->
<main class="min-h-dvh flex flex-col" style="margin-left: 0; background: var(--bg-app);">
	<!-- Desktop offset for sidebar -->
	<div class="hidden md:block" style="margin-left: var(--sidebar-width);"></div>

	<div class="flex-1 flex flex-col md:ml-[var(--sidebar-width)]">
		<!-- Chat header (during conversation) -->
		{#if messages.length > 0}
			<div class="flex items-center justify-between px-4 md:px-8 py-3 shrink-0" style="border-bottom: 1px solid var(--border);">
				<div class="flex items-center gap-2">
					<img src="/mascot-sm.png" alt="" class="w-5 h-5" />
					<span class="text-sm font-medium" style="color: var(--text-primary);">{agentName}</span>
				</div>
				<div class="flex items-center gap-2">
					<a
						href="/call/{agentId}"
						class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
						style="background: #10B981; color: white;"
					>
						📞 Call
					</a>
				</div>
			</div>
		{/if}

		<!-- Messages or Welcome -->
		<div class="flex-1 overflow-y-auto">
			{#if messages.length === 0}
				<WelcomeScreen onSend={sendMessage} />
			{:else}
				<div class="max-w-[var(--content-max)] mx-auto px-4 md:px-8 py-6 space-y-6">
					{#each messages as msg, i}
						{#if msg.role === 'user'}
							<div class="flex justify-end">
								<div class="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-tr-md text-[15px]" style="background: var(--accent); color: white;">
									{msg.content}
								</div>
							</div>
						{:else if msg.role === 'tool'}
							<div class="flex gap-3">
								<div class="w-6 h-6 flex-shrink-0 mt-0.5 flex items-center justify-center rounded-full" style="background: var(--bg-hover);">
									<span class="text-xs">🔧</span>
								</div>
								<div class="max-w-[85%] px-3 py-2 rounded-xl text-xs" style="background: var(--bg-secondary); border: 1px solid var(--border);">
									<span class="font-medium" style="color: var(--text-muted);">{msg.tool_name}</span>
									<pre class="mt-1 whitespace-pre-wrap" style="color: var(--text-secondary);">{msg.content}</pre>
								</div>
							</div>
						{:else}
							<div class="flex gap-3">
								<img src="/mascot-sm.png" alt="" class="w-6 h-6 flex-shrink-0 mt-0.5" />
								<div class="max-w-[85%]">
									<div class="chat-prose text-[15px] leading-relaxed" style="color: var(--text-primary);">
										{@html renderMarkdown(msg.content)}
										{#if streaming && i === messages.length - 1 && msg.content}
											<StreamingIndicator />
										{/if}
									</div>
									{#if !streaming && msg.content}
										<div class="flex items-center gap-3 mt-2">
											<button
												onclick={() => playTTS(msg.content, msg.content.slice(0, 20))}
												class="text-xs flex items-center gap-1 transition-opacity hover:opacity-70"
												style="color: var(--text-muted);"
											>
												{playingTTS === msg.content.slice(0, 20) ? '⏹ Stop' : '🔊 Listen'}
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
			<div class="max-w-[var(--content-max)] mx-auto px-4 pb-2">
				<div class="text-sm px-3 py-2 rounded-lg" style="background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;">
					{error}
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
	</div>
</main>
