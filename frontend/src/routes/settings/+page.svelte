<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	interface VoiceProvider {
		id: string;
		name: string;
		provider_type: string;
		capability: string;
		base_url: string;
		stt_model: string;
		tts_model: string;
		tts_voice: string;
		is_verified: boolean;
	}

	let providers = $state<VoiceProvider[]>([]);
	let loading = $state(true);
	let showForm = $state(false);
	let saving = $state(false);
	let error = $state('');

	// Form state
	let name = $state('OpenAI Voice');
	let providerType = $state('openai');
	let capability = $state('both');
	let baseUrl = $state('https://api.openai.com/v1');
	let apiKey = $state('');
	let sttModel = $state('whisper-1');
	let ttsModel = $state('tts-1');
	let ttsVoice = $state('alloy');

	const voices = ['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer'];

	const presets: Record<string, { name: string; base_url: string; stt_model: string; tts_model: string; note: string }> = {
		openai: {
			name: 'OpenAI',
			base_url: 'https://api.openai.com/v1',
			stt_model: 'whisper-1',
			tts_model: 'tts-1',
			note: 'Get API key from platform.openai.com/api-keys',
		},
		custom: {
			name: 'Custom (OpenAI-compatible)',
			base_url: '',
			stt_model: 'whisper-1',
			tts_model: 'tts-1',
			note: 'Any endpoint compatible with OpenAI /audio/speech and /audio/transcriptions',
		},
	};

	function applyPreset(type: string) {
		providerType = type;
		const p = presets[type];
		if (p) {
			name = p.name + ' Voice';
			baseUrl = p.base_url;
			sttModel = p.stt_model;
			ttsModel = p.tts_model;
		}
	}

	onMount(async () => {
		try {
			providers = await api<VoiceProvider[]>('/voice/providers');
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	});

	async function save() {
		if (!apiKey.trim() && providerType !== 'edge') {
			error = 'API key is required';
			return;
		}
		saving = true;
		error = '';
		try {
			const vp = await api<VoiceProvider>('/voice/providers', {
				method: 'POST',
				body: JSON.stringify({
					name,
					provider_type: providerType,
					capability,
					base_url: baseUrl,
					api_key: apiKey,
					stt_model: sttModel,
					tts_model: ttsModel,
					tts_voice: ttsVoice,
				}),
			});
			providers = [...providers, vp];
			showForm = false;
			apiKey = '';
		} catch (e: any) {
			error = e.message;
		} finally {
			saving = false;
		}
	}

	async function remove(id: string) {
		try {
			// No delete endpoint yet, just filter locally
			providers = providers.filter(p => p.id !== id);
		} catch (e: any) {
			error = e.message;
		}
	}
</script>

<div class="min-h-screen bg-gray-950 text-white">
	<nav class="border-b border-gray-800 px-6 py-4 flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Dashboard</a>
			<h1 class="text-xl font-bold">Voice Settings</h1>
		</div>
		<button
			onclick={() => { showForm = !showForm; if (showForm) applyPreset('openai'); }}
			class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm"
		>
			{showForm ? 'Cancel' : '+ Add Voice Provider'}
		</button>
	</nav>

	<main class="max-w-3xl mx-auto px-6 py-8">
		{#if loading}
			<p class="text-gray-400">Loading...</p>
		{:else}
			{#if error && !showForm}
				<div class="bg-red-950 border border-red-900 rounded-lg px-4 py-3 mb-6 text-sm text-red-400">{error}</div>
			{/if}

			{#if showForm}
				<div class="bg-gray-900 border border-blue-500/30 rounded-xl p-6 mb-8">
					<h2 class="text-lg font-semibold mb-4">Add Voice Provider</h2>

					<!-- Preset selector -->
					<div class="flex gap-2 mb-5">
						{#each Object.entries(presets) as [key, preset]}
							<button
								onclick={() => applyPreset(key)}
								class="px-3 py-1.5 rounded-lg text-sm {providerType === key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}"
							>
								{preset.name}
							</button>
						{/each}
					</div>

					<p class="text-gray-500 text-xs mb-4">{presets[providerType]?.note || ''}</p>

					<div class="space-y-4">
						<div>
							<label for="vp-name" class="block text-sm text-gray-300">Name</label>
							<input id="vp-name" bind:value={name} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
						</div>

						<div>
							<label for="vp-url" class="block text-sm text-gray-300">Base URL</label>
							<input id="vp-url" bind:value={baseUrl} placeholder="https://api.openai.com/v1" class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
						</div>

						<div>
							<label for="vp-key" class="block text-sm text-gray-300">API Key</label>
							<input id="vp-key" type="password" bind:value={apiKey} placeholder="sk-..." class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
						</div>

						<div class="grid grid-cols-3 gap-4">
							<div>
								<label for="vp-stt" class="block text-sm text-gray-300">STT Model</label>
								<input id="vp-stt" bind:value={sttModel} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm" />
							</div>
							<div>
								<label for="vp-tts" class="block text-sm text-gray-300">TTS Model</label>
								<input id="vp-tts" bind:value={ttsModel} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm" />
							</div>
							<div>
								<label for="vp-voice" class="block text-sm text-gray-300">Voice</label>
								<select id="vp-voice" bind:value={ttsVoice} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm">
									{#each voices as v}
										<option value={v}>{v}</option>
									{/each}
								</select>
							</div>
						</div>

						<div>
							<label for="vp-cap" class="block text-sm text-gray-300">Capability</label>
							<select id="vp-cap" bind:value={capability} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white">
								<option value="both">Both (STT + TTS)</option>
								<option value="tts">TTS only</option>
								<option value="stt">STT only</option>
							</select>
						</div>
					</div>

					{#if error}
						<p class="text-red-400 text-sm mt-3">{error}</p>
					{/if}

					<div class="flex gap-3 mt-5">
						<button onclick={save} disabled={saving} class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium">
							{saving ? 'Testing & saving...' : 'Test & Save'}
						</button>
						<button onclick={() => { showForm = false; error = ''; }} class="px-6 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">
							Cancel
						</button>
					</div>
				</div>
			{/if}

			<!-- Existing providers -->
			{#if providers.length === 0 && !showForm}
				<div class="bg-gray-900 border border-gray-800 border-dashed rounded-xl p-12 text-center">
					<p class="text-4xl mb-3">🎤</p>
					<p class="text-gray-400 font-medium">No voice provider configured</p>
					<p class="text-gray-500 text-sm mt-2">
						Add a voice provider to enable speech-to-text (mic input) and text-to-speech (listen to responses) in chat.
					</p>
					<button onclick={() => { showForm = true; applyPreset('openai'); }} class="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm">
						+ Add Voice Provider
					</button>
				</div>
			{:else if providers.length > 0}
				<div class="space-y-3">
					{#each providers as vp}
						<div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
							<div class="flex items-center gap-3">
								<div class="w-10 h-10 bg-purple-900/50 border border-purple-800 rounded-lg flex items-center justify-center text-lg">
									🎤
								</div>
								<div>
									<h3 class="font-medium">{vp.name}</h3>
									<p class="text-gray-500 text-xs">
										{vp.tts_model} · voice: {vp.tts_voice} · {vp.capability}
									</p>
								</div>
							</div>
							<div class="flex items-center gap-3">
								{#if vp.is_verified}
									<span class="text-green-400 text-xs flex items-center gap-1">
										<span class="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
										Verified
									</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<!-- Info -->
			<div class="mt-8 bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-sm text-gray-500">
				<p class="font-medium text-gray-400 mb-1">💡 How voice works</p>
				<p>
					<strong>🎤 Speech-to-text:</strong> Click the mic button in chat, speak, and your voice is transcribed and sent as a message.<br/>
					<strong>🔊 Text-to-speech:</strong> Click "Listen" on any agent response to hear it read aloud.<br/>
					OpenAI's Whisper (STT) and TTS API are the default. Any OpenAI-compatible voice endpoint works.
				</p>
			</div>
		{/if}
	</main>
</div>
