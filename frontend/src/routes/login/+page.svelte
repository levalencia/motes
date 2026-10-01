<script lang="ts">
	import { goto } from '$app/navigation';
	import { login } from '$lib/api/client';
	import { setAuth } from '$lib/stores/auth';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin() {
		if (!username || !password) return;
		loading = true;
		error = '';
		try {
			const data = await login(username.toLowerCase(), password);
			setAuth(data.token, data.username);
			goto('/dashboard');
		} catch (e: any) {
			error = e.message || 'Login failed';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-dvh flex items-center justify-center px-4" style="background: var(--bg-secondary);">
	<div class="w-full max-w-sm">
		<!-- Logo -->
		<div class="flex flex-col items-center mb-8">
			<img src="/mascot.png" alt="Motes" class="w-20 h-20 object-contain mascot-float mb-4" />
			<h1 class="text-2xl font-semibold" style="color: var(--text-primary);">Motes</h1>
		</div>

		<!-- Form -->
		<div class="p-6 rounded-2xl" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-md);">
			{#if error}
				<div class="mb-4 px-3 py-2 rounded-xl text-sm" style="background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;">
					{error}
				</div>
			{/if}

			<form onsubmit={(e) => { e.preventDefault(); handleLogin(); }} class="space-y-4">
				<div>
					<label for="username" class="block text-sm font-medium mb-1.5" style="color: var(--text-secondary);">Username</label>
					<input
						id="username"
						bind:value={username}
						type="text"
						required
						placeholder="Enter username"
						class="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none transition-all duration-150 focus:ring-2 focus:ring-offset-1"
						style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary); --tw-ring-color: var(--accent);"
					/>
				</div>
				<div>
					<label for="password" class="block text-sm font-medium mb-1.5" style="color: var(--text-secondary);">Password</label>
					<input
						id="password"
						bind:value={password}
						type="password"
						required
						placeholder="Enter password"
						class="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none transition-all duration-150 focus:ring-2 focus:ring-offset-1"
						style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary); --tw-ring-color: var(--accent);"
					/>
				</div>
				<button
					type="submit"
					disabled={loading}
					class="w-full py-2.5 rounded-xl text-sm font-medium text-white transition-all duration-200 disabled:opacity-50"
					style="background: linear-gradient(135deg, var(--color-motes-blue), var(--color-motes-purple));"
				>
					{loading ? 'Signing in...' : 'Sign In'}
				</button>
			</form>
		</div>
	</div>
</div>
