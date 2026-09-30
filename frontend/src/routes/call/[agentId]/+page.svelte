<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';

	const agentId = $derived($page.params.agentId);

	let agentName = $state('Agent');
	let status = $state('Connecting...');
	let callDuration = $state(0);
	let durationInterval: ReturnType<typeof setInterval> | null = null;
	let connected = $state(false);
	let speaking = $state(false);
	let listening = $state(false);
	let transcripts = $state<{role: string; text: string}[]>([]);
	let showCaptions = $state(false);
	let socket: WebSocket | null = null;
	let audioContext: AudioContext | null = null;
	let micStream: MediaStream | null = null;
	let processor: ScriptProcessorNode | null = null;
	let audioChunksFromAzure: string[] = [];

	// Convert base64 PCM16 chunks to a single Uint8Array
	function concatBase64PCM(chunks: string[]): Uint8Array {
		const arrays = chunks.map(c => Uint8Array.from(atob(c), ch => ch.charCodeAt(0)));
		const total = arrays.reduce((s, a) => s + a.length, 0);
		const result = new Uint8Array(total);
		let offset = 0;
		for (const a of arrays) {
			result.set(a, offset);
			offset += a.length;
		}
		return result;
	}

	// Wrap raw PCM16 in a WAV header so the browser can play it
	function pcm16ToWav(pcmData: Uint8Array, sampleRate: number): Blob {
		const numChannels = 1;
		const bitsPerSample = 16;
		const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
		const blockAlign = numChannels * (bitsPerSample / 8);
		const dataSize = pcmData.length;
		const buffer = new ArrayBuffer(44 + dataSize);
		const view = new DataView(buffer);

		// RIFF header
		writeString(view, 0, 'RIFF');
		view.setUint32(4, 36 + dataSize, true);
		writeString(view, 8, 'WAVE');
		// fmt chunk
		writeString(view, 12, 'fmt ');
		view.setUint32(16, 16, true);
		view.setUint16(20, 1, true); // PCM
		view.setUint16(22, numChannels, true);
		view.setUint32(24, sampleRate, true);
		view.setUint32(28, byteRate, true);
		view.setUint16(32, blockAlign, true);
		view.setUint16(34, bitsPerSample, true);
		// data chunk
		writeString(view, 36, 'data');
		view.setUint32(40, dataSize, true);
		new Uint8Array(buffer, 44).set(pcmData);

		return new Blob([buffer], { type: 'audio/wav' });
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

		// Connect WebSocket
		socket = new WebSocket(`ws://localhost:8001/api/realtime-call/${agentId}`);

		socket.onopen = () => {
			socket!.send(JSON.stringify({
				type: 'auth',
				token,
			}));
		};

		socket.onmessage = async (event) => {
			const msg = JSON.parse(event.data);

			if (msg.type === 'ready') {
				connected = true;
				status = 'Connected';
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
				transcripts = [...transcripts, { role: 'assistant', text: msg.text }];
				status = 'Speaking...';
				speaking = true;
			} else if (msg.type === 'response_transcript') {
				// Live streaming text — update or add
				const last = transcripts[transcripts.length - 1];
				if (last && last.role === 'assistant') {
					transcripts = [...transcripts.slice(0, -1), { role: 'assistant', text: msg.text }];
				} else {
					transcripts = [...transcripts, { role: 'assistant', text: msg.text }];
				}
			} else if (msg.type === 'audio_wav') {
				// Server-assembled WAV from Azure Realtime
				const bytes = Uint8Array.from(atob(msg.data), c => c.charCodeAt(0));
				const blob = new Blob([bytes], { type: 'audio/wav' });
				const url = URL.createObjectURL(blob);
				const audio = new Audio(url);
				audio.onended = () => {
					URL.revokeObjectURL(url);
					speaking = false;
					status = 'Listening...';
					listening = true;
					startRecordingChunk();
				};
				stopRecording();
				speaking = true;
				status = 'Speaking...';
				audio.play();
			} else if (msg.type === 'response_done') {
				// Final text — DON'T add again (already shown via response_transcript)
			} else if (msg.type === 'audio') {
				// Ignore individual PCM chunks (server assembles WAV now)
			} else if (msg.type === 'audio_mp3') {
				// Pipeline fallback (Edge TTS mp3)
				const bytes = Uint8Array.from(atob(msg.data), c => c.charCodeAt(0));
				const blob = new Blob([bytes], { type: 'audio/mpeg' });
				const url = URL.createObjectURL(blob);
				const audio = new Audio(url);
				audio.onended = () => {
					URL.revokeObjectURL(url);
					speaking = false;
					status = 'Listening...';
					listening = true;
					startRecordingChunk();
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
		if (!connected) return;
		navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
			micStream = stream;
			recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
			const chunks: Blob[] = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunks.push(e.data);
			};
			recorder.onstop = () => {
				// Send the complete webm blob
				const blob = new Blob(chunks, { type: 'audio/webm' });
				if (blob.size > 0 && socket && socket.readyState === WebSocket.OPEN) {
					const reader = new FileReader();
					reader.onload = () => {
						const base64 = (reader.result as string).split(',')[1];
						socket!.send(JSON.stringify({ type: 'audio', data: base64 }));
					};
					reader.readAsDataURL(blob);
				}
				// Start next recording cycle if still listening
				if (connected && listening) {
					startContinuousRecording();
				}
			};
			recorder.start();
			// Record for 6 seconds then send (long enough for full sentences)
			setTimeout(() => {
				if (recorder && recorder.state === 'recording') {
					recorder.stop();
					// Don't stop the mic stream — it'll be reused
				}
			}, 6000);
		});
	}

	function startRecordingChunk() {
		// Resume continuous recording after agent responds
		startContinuousRecording();
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

<div class="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center relative">
	<!-- Background pulse animation when listening -->
	{#if listening}
		<div class="absolute inset-0 flex items-center justify-center pointer-events-none">
			<div class="w-64 h-64 rounded-full bg-green-500/10 animate-ping" style="animation-duration: 2s;"></div>
		</div>
	{/if}
	{#if speaking}
		<div class="absolute inset-0 flex items-center justify-center pointer-events-none">
			<div class="w-64 h-64 rounded-full bg-blue-500/10 animate-ping" style="animation-duration: 1.5s;"></div>
		</div>
	{/if}

	<!-- Mascot -->
	<img src="/mascot.png" alt="Motes" class="w-32 h-32 object-contain mb-4 {speaking ? 'animate-bounce' : ''}" style="animation-duration: 1s;" />

	<!-- Agent name -->
	<h1 class="text-2xl font-bold mb-1">{agentName}</h1>

	<!-- Status -->
	<p class="text-gray-400 text-sm mb-2">{status}</p>

	<!-- Duration -->
	{#if connected}
		<p class="text-gray-500 text-xs font-mono mb-8">{formatDuration(callDuration)}</p>
	{/if}

	<!-- Live transcript (toggleable) -->
	{#if showCaptions}
		<div class="w-full max-w-md px-4 mb-8 space-y-2 min-h-[80px]">
			{#each transcripts.slice(-3) as t}
				<div class="text-center">
					{#if t.role === 'user'}
						<p class="text-gray-400 text-sm italic">"{t.text}"</p>
					{:else}
						<p class="text-white text-sm">"{t.text}"</p>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<div class="mb-8"></div>
	{/if}

	<!-- Controls -->
	<div class="flex items-center gap-8">
		<!-- Mute (placeholder) -->
		<button class="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center text-xl hover:bg-gray-700" title="Mute">
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
			class="w-14 h-14 rounded-full {showCaptions ? 'bg-blue-700' : 'bg-gray-800'} flex items-center justify-center text-xl hover:bg-gray-700"
			title="Toggle captions"
		>
			💬
		</button>
	</div>

	<!-- Back to chat link -->
	<p class="text-gray-600 text-xs mt-8">
		Call transcript is saved to your conversation
	</p>
</div>
