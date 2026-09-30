<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/api/client';
	import { setAuth } from '$lib/stores/auth';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin() {
		error = '';
		loading = true;
		try {
			const result = await login(username, password);
			setAuth(result.token, result.username);
			goto('/dashboard');
		} catch (e: any) {
			error = e.message;
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen bg-gray-950 flex items-center justify-center px-4">
	<div class="max-w-md w-full space-y-8">
		<div class="text-center">
			<h1 class="text-4xl font-bold text-white">Motes</h1>
			<p class="mt-2 text-gray-400">Sign in to your account</p>
		</div>

		<form onsubmit={(e) => { e.preventDefault(); handleLogin(); }} class="space-y-4">
			<div>
				<label for="username" class="block text-sm text-gray-300">Username</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					required
					class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-blue-500"
				/>
			</div>
			<div>
				<label for="password" class="block text-sm text-gray-300">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					class="w-full mt-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:border-blue-500"
				/>
			</div>
			{#if error}
				<p class="text-red-400 text-sm">{error}</p>
			{/if}
			<button
				type="submit"
				disabled={loading}
				class="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded font-medium"
			>
				{loading ? 'Signing in...' : 'Sign In'}
			</button>
		</form>
	</div>
</div>
