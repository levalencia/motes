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

	// Realtime config state
	let realtimeUrl = $state('');
	let realtimeKey = $state('');
	let realtimeConfigured = $state(false);
	let realtimeSaving = $state(false);

	// Proactive intelligence state
	let proactiveEnabled = $state(false);
	let proactiveInterval = $state(60);
	let proactiveSaving = $state(false);
	let proactiveSaved = $state(false);
	const intervalOptions = [
		{ value: 15, label: '15 min' },
		{ value: 30, label: '30 min' },
		{ value: 60, label: '1 hour' },
		{ value: 120, label: '2 hours' },
		{ value: 240, label: '4 hours' },
		{ value: 480, label: '8 hours' },
		{ value: 1440, label: '24 hours' },
	];

	// Agent personality state
	let agentId = $state('');
	let agentName = $state('Motes');
	let systemPrompt = $state('');
	let voicePersonality = $state('');
	let personalitySaving = $state(false);
	let personalitySaved = $state(false);

	const personalityPresets: Record<string, { label: string; emoji: string; prompt: string; voice: string }> = {
		friendly: {
			label: 'Friendly Assistant',
			emoji: '😊',
			prompt: 'You are Motes, a warm and friendly AI assistant. You are helpful, encouraging, and use casual language. You remember things about the user and bring them up naturally.',
			voice: '',
		},
		professional: {
			label: 'Professional',
			emoji: '💼',
			prompt: 'You are Motes, a concise professional assistant. Be direct, efficient, and actionable. Use bullet points when listing items. No small talk unless the user initiates.',
			voice: '',
		},
		spanish_paisa: {
			label: 'Paisa Colombiano',
			emoji: '🇨🇴',
			prompt: 'Eres Motes, un asistente personal amigable con estilo paisa colombiano. Siempre respondes en español con tono cálido, cercano y coloquial. Usas expresiones paisas cuando es natural. Recuerdas lo que el usuario te dice.',
			voice: 'Colombian paisa Spanish accent, warm and casual',
		},
		french: {
			label: 'Français',
			emoji: '🇫🇷',
			prompt: 'Tu es Motes, un assistant personnel sympathique. Tu réponds toujours en français avec un ton chaleureux et professionnel. Tu te souviens des détails personnels de l\'utilisateur.',
			voice: 'Native French accent, warm and professional',
		},
		bilingual: {
			label: 'Bilingual ES/EN',
			emoji: '🌍',
			prompt: 'You are Motes, a bilingual assistant. Detect the user\'s language and respond in that language. Switch seamlessly between English and Spanish. Be warm and helpful.',
			voice: '',
		},
		sarcastic: {
			label: 'Witty & Sarcastic',
			emoji: '😏',
			prompt: 'You are Motes, a witty assistant with a dry sense of humor. You\'re helpful but add clever observations and light sarcasm. Never mean — just entertaining. Get the job done with personality.',
			voice: '',
		},
	};

	function applyPersonalityPreset(key: string) {
		const p = personalityPresets[key];
		if (p) {
			systemPrompt = p.prompt;
			if (p.voice) voicePersonality = p.voice;
		}
	}

	let resetting = $state(false);
	let resetDone = $state(false);

	async function resetAll() {
		if (!confirm('This will delete ALL messages, memories, patterns, and notifications. Are you sure?')) return;
		resetting = true;
		try {
			await api(`/agents/${agentId}/reset`, { method: 'DELETE' });
			resetDone = true;
			setTimeout(() => resetDone = false, 3000);
		} catch (e: any) {
			error = e.message;
		} finally {
			resetting = false;
		}
	}

	async function savePersonality() {
		personalitySaving = true;
		personalitySaved = false;
		try {
			if (agentId) {
				await api(`/agents/${agentId}/personality`, {
					method: 'PUT',
					body: JSON.stringify({ name: agentName, system_prompt: systemPrompt }),
				});
			}
			await api('/voice/voice-personality', {
				method: 'POST',
				body: JSON.stringify({ personality: voicePersonality }),
			});
			personalitySaved = true;
			setTimeout(() => personalitySaved = false, 3000);
		} catch (e: any) {
			if (e?.message?.includes('401') || e?.message?.includes('expired') || e?.message?.includes('Invalid')) {
				goto('/login');
				return;
			}
			error = e.message;
		} finally {
			personalitySaving = false;
		}
	}

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
			// Load realtime config
			const rtConfig = await api<{ realtime_url: string; has_key: boolean }>('/voice/realtime-config');
			realtimeUrl = rtConfig.realtime_url;
			realtimeConfigured = rtConfig.has_key;
			// Load proactive settings
			try {
				const ps = await api<{ enabled: boolean; interval_minutes: number }>('/voice/proactive-settings');
				proactiveEnabled = ps.enabled;
				proactiveInterval = ps.interval_minutes;
			} catch { /* endpoint may not exist yet */ }
			// Load agent personality
			const agents = await api<{ id: string; name: string }[]>('/agents');
			if (agents.length > 0) {
				agentId = agents[0].id;
				const personality = await api<{ name: string; system_prompt: string; voice_personality: string }>(`/agents/${agentId}/personality`);
				agentName = personality.name;
				systemPrompt = personality.system_prompt;
				voicePersonality = personality.voice_personality || '';
			}
		} catch (e: any) {
			if (e?.message?.includes('401')) goto('/login');
		} finally {
			loading = false;
		}
	});

	async function saveRealtimeConfig() {
		realtimeSaving = true;
		try {
			const result = await api<{ realtime_url: string; has_key: boolean }>('/voice/realtime-config', {
				method: 'POST',
				body: JSON.stringify({ realtime_url: realtimeUrl, realtime_key: realtimeKey }),
			});
			realtimeConfigured = result.has_key;
			realtimeKey = '';
		} catch (e: any) {
			error = e.message;
		} finally {
			realtimeSaving = false;
		}
	}

	async function handleSaveProactive() {
		proactiveSaving = true;
		proactiveSaved = false;
		try {
			await api('/voice/proactive-settings', {
				method: 'POST',
				body: JSON.stringify({ enabled: proactiveEnabled, interval_minutes: proactiveInterval }),
			});
			proactiveSaved = true;
			setTimeout(() => proactiveSaved = false, 3000);
		} catch (e: any) {
			error = e.message;
		} finally {
			proactiveSaving = false;
		}
	}

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
			<a href="/dashboard" class="text-gray-400 hover:text-white">← Back</a>
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

			<!-- Agent Personality -->
			<div class="mb-8">
				<h2 class="text-lg font-semibold mb-4">🎭 Agent Personality</h2>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
					<p class="text-gray-400 text-sm mb-4">Choose a preset or customize how Motes talks and behaves.</p>

					<!-- Preset grid -->
					<div class="grid grid-cols-3 gap-2 mb-5">
						{#each Object.entries(personalityPresets) as [key, preset]}
							<button
								onclick={() => applyPersonalityPreset(key)}
								class="p-3 rounded-lg text-left border transition-colors {systemPrompt === preset.prompt ? 'bg-blue-900/30 border-blue-500' : 'bg-gray-800 border-gray-700 hover:border-gray-600'}"
							>
								<span class="text-xl">{preset.emoji}</span>
								<p class="text-sm font-medium mt-1">{preset.label}</p>
							</button>
						{/each}
					</div>

					<!-- Custom fields -->
					<div class="space-y-4">
						<div>
							<label for="agent-name" class="block text-sm text-gray-300">Agent Name</label>
							<input id="agent-name" bind:value={agentName} class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white" />
						</div>
						<div>
							<label for="sys-prompt" class="block text-sm text-gray-300">System Prompt</label>
							<textarea
								id="sys-prompt"
								bind:value={systemPrompt}
								rows="4"
								placeholder="Describe how Motes should behave, what language to use, personality traits..."
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-600"
							></textarea>
						</div>
						<div>
							<label for="voice-pers" class="block text-sm text-gray-300">Voice Accent (for calls)</label>
							<input
								id="voice-pers"
								bind:value={voicePersonality}
								placeholder="e.g., Colombian paisa Spanish, warm and casual"
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-600"
							/>
						</div>
					</div>
					<div class="flex items-center gap-3 mt-4">
						<button
							onclick={savePersonality}
							disabled={personalitySaving}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
						>
							{personalitySaving ? 'Saving...' : 'Save Personality'}
						</button>
						{#if personalitySaved}
							<span class="text-green-400 text-sm">✓ Saved!</span>
						{/if}
					</div>
				</div>
			</div>

			<!-- Proactive Intelligence -->
			<div class="mb-8">
				<h2 class="text-lg font-semibold mb-4">💡 Proactive Intelligence</h2>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
					<p class="text-gray-400 text-sm mb-4">
						When enabled, Motes will periodically check your connected services and proactively push insights to your thread.
					</p>

					<!-- Enable toggle -->
					<div class="flex items-center justify-between mb-5">
						<div>
							<p class="text-sm font-medium">Enable proactive messages</p>
							<p class="text-xs text-gray-500 mt-0.5">Motes will send you insights without being asked</p>
						</div>
						<button
							onclick={() => { proactiveEnabled = !proactiveEnabled; }}
							class="relative w-11 h-6 rounded-full transition-colors duration-200"
							style="background: {proactiveEnabled ? '#10B981' : '#374151'};"
						>
							<span
								class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
								style="transform: translateX({proactiveEnabled ? '20px' : '0'});"
							></span>
						</button>
					</div>

					<!-- Interval selector -->
					<div class="mb-5">
						<label for="proactive-interval" class="block text-sm text-gray-300 mb-2">Check interval</label>
						<div class="flex flex-wrap gap-2">
							{#each intervalOptions as opt}
								<button
									onclick={() => { proactiveInterval = opt.value; }}
									class="px-3 py-1.5 rounded-lg text-sm transition-colors {proactiveInterval === opt.value ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}"
									disabled={!proactiveEnabled}
								>
									{opt.label}
								</button>
							{/each}
						</div>
					</div>

					<div class="flex items-center gap-3">
						<button
							onclick={handleSaveProactive}
							disabled={proactiveSaving}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
						>
							{proactiveSaving ? 'Saving...' : 'Save'}
						</button>
						{#if proactiveSaved}
							<span class="text-green-400 text-sm">✓ Saved!</span>
						{/if}
					</div>
				</div>
			</div>

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
					<strong>🎤 Speech-to-text:</strong> Uses local Whisper (free) by default. Add a provider for cloud STT.<br/>
					<strong>🔊 Text-to-speech:</strong> Uses Edge TTS (free) by default. Add a provider for premium voices.<br/>
					<strong>📞 Voice calls:</strong> Pipeline mode (free) or Azure Realtime (sub-second, configure below).
				</p>
			</div>

			<!-- Realtime Voice Call Config -->
			<div class="mt-8">
				<h2 class="text-lg font-semibold mb-4">📞 Realtime Voice Calls</h2>
				<div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
					<p class="text-gray-400 text-sm mb-4">
						For sub-second voice calls (like OpenAI Dots), configure an Azure OpenAI Realtime model.
						Without this, calls use the pipeline mode (Whisper → LLM → Edge TTS, ~3s latency).
					</p>
					<div class="space-y-4">
						<div>
							<label for="rt-url" class="block text-sm text-gray-300">Realtime WebSocket URL</label>
							<input
								id="rt-url"
								bind:value={realtimeUrl}
								placeholder="wss://your-resource.openai.azure.com/openai/v1/realtime?model=gpt-realtime-2.1-mini"
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-600"
							/>
						</div>
						<div>
							<label for="rt-key" class="block text-sm text-gray-300">API Key</label>
							<input
								id="rt-key"
								type="password"
								bind:value={realtimeKey}
								placeholder={realtimeConfigured ? '••••••••••••••••' : 'Enter your Azure OpenAI API key'}
								class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm placeholder-gray-600"
							/>
						</div>
					</div>
					<div class="flex items-center gap-3 mt-4">
						<button
							onclick={saveRealtimeConfig}
							disabled={realtimeSaving}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium"
						>
							{realtimeSaving ? 'Saving...' : 'Save'}
						</button>
						{#if realtimeConfigured}
							<span class="text-green-400 text-xs">✓ Realtime configured</span>
						{:else}
							<span class="text-gray-500 text-xs">Not configured — using pipeline mode</span>
						{/if}
					</div>
				</div>
			</div>

			<!-- Danger Zone -->
			<div class="mt-8">
				<h2 class="text-lg font-semibold mb-4 text-red-400">⚠️ Danger Zone</h2>
				<div class="bg-gray-900 border border-red-900/50 rounded-xl p-6">
					<p class="text-gray-400 text-sm mb-4">
						Delete all messages, call history, memories, learned patterns, and notifications. This cannot be undone.
					</p>
					<div class="flex items-center gap-3">
						<button
							onclick={resetAll}
							disabled={resetting}
							class="px-6 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 rounded-lg text-sm font-medium text-white"
						>
							{resetting ? 'Resetting...' : 'Reset Everything'}
						</button>
						{#if resetDone}
							<span class="text-green-400 text-sm">✓ Reset complete</span>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</main>
</div>
