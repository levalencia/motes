<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';

	const agentId = $derived($page.params.agentId);

	let agentName = $state('Motes');
	let status = $state('Connecting...');
	let callDuration = $state(0);
	let durationInterval: ReturnType<typeof setInterval> | null = null;
	let connected = $state(false);
	let speaking = $state(false);
	let listening = $state(false);
	let transcripts = $state<{role: string; text: string}[]>([]);
	let showCaptions = $state(false);
	let showTranscript = $state(false);
	let previousMessages = $state<{role: string; content: string}[]>([]);
	let conversationId = $state<string | null>(null);
	let socket: WebSocket | null = null;
	let micStream: MediaStream | null = null;

	async function playRingTone(): Promise<void> {
		const ctx = new AudioContext();
		// Two ring tones like a phone
		for (let ring = 0; ring < 2; ring++) {
			const osc = ctx.createOscillator();
			const gain = ctx.createGain();
			osc.connect(gain);
			gain.connect(ctx.destination);
			osc.frequency.value = 440;
			gain.gain.value = 0.15;
			osc.start();
			// Ring for 0.4s
			await new Promise(r => setTimeout(r, 400));
			osc.stop();
			// Pause 0.3s between rings
			if (ring < 1) await new Promise(r => setTimeout(r, 300));
		}
		// Brief pause before "answering"
		await new Promise(r => setTimeout(r, 500));
		ctx.close();
	}

	function writeString(view: DataView, offset: number, str: string) {
		for (let i = 0; i < str.length; i++) {
			view.setUint8(offset + i, str.charCodeAt(i));
		}
	}

	onMount(async () => {
		const token = localStorage.getItem('motes_token');
		if (!token) { goto('/login'); return; }

		// Get agent name
		try {
			const res = await fetch('http://localhost:8001/api/agents', {
				headers: { Authorization: `Bearer ${token}` }
			});
			const agents = await res.json();
			const agent = agents.find((a: any) => a.id === agentId);
			if (agent) agentName = agent.name;
		} catch { /* ignore */ }

		// Check for existing conversation from URL
		const urlConvId = $page.url.searchParams.get('conversation');
		if (urlConvId) {
			conversationId = urlConvId;
			// Load previous transcript
			try {
				const res = await fetch(`http://localhost:8001/api/conversations/${urlConvId}/messages`, {
					headers: { Authorization: `Bearer ${token}` }
				});
				if (res.ok) {
					previousMessages = await res.json();
				}
			} catch { /* ignore */ }
		}

		// Connect WebSocket
		socket = new WebSocket(`ws://localhost:8001/api/realtime-call/${agentId}`);

		socket.onopen = () => {
			status = 'Ringing...';
			// Play ring tone, then send auth after 2 rings
			playRingTone().then(() => {
				socket!.send(JSON.stringify({
					type: 'auth',
					token,
					conversation_id: conversationId,
				}));
			});
		};

		socket.onmessage = async (event) => {
			const msg = JSON.parse(event.data);

			if (msg.type === 'ready') {
				connected = true;
				status = 'Connected';
				if (msg.conversation_id) conversationId = msg.conversation_id;
				startTimer();
				startMic();
			} else if (msg.type === 'status') {
				status = msg.text;
				listening = msg.text === 'Listening...';
				speaking = msg.text === 'Speaking...';
			} else if (msg.type === 'user_transcript') {
				transcripts = [...transcripts, { role: 'user', text: msg.text }];
				listening = false;
			} else if (msg.type === 'response_done') {
				if (msg.text) {
					// Only add if not duplicate of last transcript
					const last = transcripts[transcripts.length - 1];
					if (!last || last.text !== msg.text) {
						transcripts = [...transcripts, { role: 'assistant', text: msg.text }];
					}
				}
				status = 'Speaking...';
				speaking = true;
			} else if (msg.type === 'response_transcript') {
				const last = transcripts[transcripts.length - 1];
				if (last && last.role === 'assistant') {
					transcripts = [...transcripts.slice(0, -1), { role: 'assistant', text: msg.text }];
				} else {
					transcripts = [...transcripts, { role: 'assistant', text: msg.text }];
				}
			} else if (msg.type === 'audio_wav') {
				const bytes = Uint8Array.from(atob(msg.data), c => c.charCodeAt(0));
				const blob = new Blob([bytes], { type: 'audio/wav' });
				const url = URL.createObjectURL(blob);
				const audio = new Audio(url);
				audio.onended = () => {
					URL.revokeObjectURL(url);
					speaking = false;
					status = 'Listening...';
					listening = true;
					startContinuousRecording();
				};
				stopRecording();
				speaking = true;
				status = 'Speaking...';
				audio.play();
			} else if (msg.type === 'audio_mp3') {
				const bytes = Uint8Array.from(atob(msg.data), c => c.charCodeAt(0));
				const blob = new Blob([bytes], { type: 'audio/mpeg' });
				const url = URL.createObjectURL(blob);
				const audio = new Audio(url);
				audio.onended = () => {
					URL.revokeObjectURL(url);
					speaking = false;
					status = 'Listening...';
					listening = true;
					startContinuousRecording();
				};
				stopRecording();
				audio.play();
			} else if (msg.type === 'ended') {
				hangUp();
			} else if (msg.type === 'error') {
				status = `Error: ${msg.message}`;
			}
		};

		socket.onclose = () => {
			if (connected) hangUp();
		};
	});

	onDestroy(() => {
		cleanUp();
	});

	let recorder: MediaRecorder | null = null;

	function startMic() {
		listening = true;
		status = 'Listening...';
		startContinuousRecording();
	}

	function startContinuousRecording() {
		if (!connected || recorder?.state === 'recording') return;

		const startRecording = (stream: MediaStream) => {
			recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
			const chunks: Blob[] = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunks.push(e.data);
			};
			recorder.onstop = () => {
				const blob = new Blob(chunks, { type: 'audio/webm' });
				if (blob.size > 5000 && socket && socket.readyState === WebSocket.OPEN) {
					const reader = new FileReader();
					reader.onload = () => {
						const base64 = (reader.result as string).split(',')[1];
						socket!.send(JSON.stringify({ type: 'audio', data: base64 }));
					};
					reader.readAsDataURL(blob);
				}
				if (connected && listening && !speaking) {
					setTimeout(() => startRecording(stream), 100);
				}
			};
			recorder.start();
			setTimeout(() => {
				if (recorder && recorder.state === 'recording') {
					recorder.stop();
				}
			}, 6000);
		};

		if (micStream && micStream.active) {
			startRecording(micStream);
		} else {
			navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
				micStream = stream;
				startRecording(stream);
			});
		}
	}

	function stopRecording() {
		if (recorder && recorder.state === 'recording') {
			recorder.stop();
		}
		if (micStream) {
			micStream.getTracks().forEach(t => t.stop());
			micStream = null;
		}
	}

	function startTimer() {
		durationInterval = setInterval(() => { callDuration += 1; }, 1000);
	}

	function formatDuration(s: number): string {
		const m = Math.floor(s / 60);
		const sec = s % 60;
		return `${m}:${sec.toString().padStart(2, '0')}`;
	}

	function hangUp() {
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(JSON.stringify({ type: 'end' }));
		}
		cleanUp();
		goto(`/chat/${agentId}`);
	}

	function cleanUp() {
		connected = false;
		if (durationInterval) clearInterval(durationInterval);
		stopRecording();
		if (micStream) {
			micStream.getTracks().forEach(t => t.stop());
			micStream = null;
		}
		if (socket) {
			socket.close();
			socket = null;
		}
	}
</script>

<!-- Transcript view (separate panel) -->
{#if showTranscript}
	<div class="fixed inset-0 z-50 flex" style="background: var(--bg-app);">
		<div class="flex-1 flex flex-col max-w-2xl mx-auto">
			<div class="flex items-center justify-between px-6 py-4" style="border-bottom: 1px solid var(--border);">
				<h2 class="text-lg font-semibold" style="color: var(--text-primary);">Call Transcript</h2>
				<button onclick={() => { showTranscript = false; }} class="px-3 py-1.5 rounded-lg text-sm" style="color: var(--text-secondary); background: var(--bg-hover);">
					← Back to call
				</button>
			</div>
			<div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
				<!-- Previous messages (from earlier in this conversation) -->
				{#each previousMessages as msg}
					<div class="flex gap-3">
						{#if msg.role === 'user'}
							<div class="flex justify-end w-full">
								<div class="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm" style="background: var(--accent); color: white;">{msg.content}</div>
							</div>
						{:else}
							<div class="flex gap-2">
								<img src="/mascot-sm.png" alt="" class="w-5 h-5 mt-0.5" />
								<div class="text-sm" style="color: var(--text-primary);">{msg.content}</div>
							</div>
						{/if}
					</div>
				{/each}
				{#if previousMessages.length > 0 && transcripts.length > 0}
					<div class="text-center text-xs py-2" style="color: var(--text-muted);">— Current call —</div>
				{/if}
				<!-- Current call transcripts -->
				{#each transcripts as t}
					<div class="flex gap-3">
						{#if t.role === 'user'}
							<div class="flex justify-end w-full">
								<div class="max-w-[80%] px-4 py-2.5 rounded-2xl text-sm" style="background: var(--accent); color: white;">{t.text}</div>
							</div>
						{:else}
							<div class="flex gap-2">
								<img src="/mascot-sm.png" alt="" class="w-5 h-5 mt-0.5" />
								<div class="text-sm" style="color: var(--text-primary);">{t.text}</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<!-- Call UI -->
<div class="min-h-dvh flex flex-col items-center justify-center relative" style="background: var(--bg-app); color: var(--text-primary);">
	<!-- Background pulse -->
	{#if listening}
		<div class="absolute inset-0 flex items-center justify-center pointer-events-none">
			<div class="w-64 h-64 rounded-full animate-ping" style="background: rgba(16, 185, 129, 0.08); animation-duration: 2s;"></div>
		</div>
	{/if}
	{#if speaking}
		<div class="absolute inset-0 flex items-center justify-center pointer-events-none">
			<div class="w-64 h-64 rounded-full animate-ping" style="background: rgba(79, 91, 213, 0.08); animation-duration: 1.5s;"></div>
		</div>
	{/if}

	<!-- Mascot -->
	<img src="/mascot.png" alt="Motes"
		class="w-32 h-32 object-contain mb-4 {speaking ? 'animate-bounce' : status === 'Ringing...' ? '' : 'mascot-float'}"
		style="animation-duration: {speaking ? '1s' : '4s'}; {status === 'Ringing...' ? 'animation: mascot-float 1s ease-in-out infinite;' : ''}"
	/>

	<h1 class="text-2xl font-semibold mb-1">{agentName}</h1>
	<p class="text-sm mb-2" style="color: var(--text-secondary);">{status}</p>

	{#if connected}
		<p class="text-xs font-mono mb-8" style="color: var(--text-muted);">{formatDuration(callDuration)}</p>
	{/if}

	<!-- Live captions -->
	{#if showCaptions}
		<div class="w-full max-w-md px-4 mb-8 space-y-2 min-h-[80px]">
			{#each transcripts.slice(-3) as t}
				<div class="text-center">
					{#if t.role === 'user'}
						<p class="text-sm italic" style="color: var(--text-secondary);">"{t.text}"</p>
					{:else}
						<p class="text-sm" style="color: var(--text-primary);">"{t.text}"</p>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<div class="mb-8"></div>
	{/if}

	<!-- Controls -->
	<div class="flex items-center gap-8">
		<!-- Mute -->
		<button class="w-14 h-14 rounded-full flex items-center justify-center text-xl" style="background: var(--bg-hover);" title="Mute">
			{listening ? '🎤' : '🔇'}
		</button>

		<!-- Hang up -->
		<button
			onclick={hangUp}
			class="w-16 h-16 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center text-2xl shadow-lg shadow-red-600/30"
			title="End call"
		>
			📞
		</button>

		<!-- Captions toggle -->
		<button
			onclick={() => { showCaptions = !showCaptions; }}
			class="w-14 h-14 rounded-full flex items-center justify-center text-xl"
			style="background: {showCaptions ? 'var(--accent)' : 'var(--bg-hover)'}; color: {showCaptions ? 'white' : 'inherit'};"
			title="Toggle captions"
		>
			💬
		</button>
	</div>

	<!-- Transcript button -->
	<button
		onclick={() => { showTranscript = true; }}
		class="mt-6 text-xs px-4 py-2 rounded-full transition-colors"
		style="color: var(--text-muted); background: var(--bg-hover);"
	>
		📝 View Transcript
	</button>

	<p class="text-xs mt-4" style="color: var(--text-muted);">
		{previousMessages.length > 0 ? `Continuing call (${previousMessages.length} previous messages)` : 'Call transcript is saved to your conversation'}
	</p>
</div>
