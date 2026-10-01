<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	// The chat route is deprecated — redirect to the single-thread dashboard
	onMount(() => {
		goto('/dashboard', { replaceState: true });
	});
</script>

<div class="min-h-dvh flex items-center justify-center" style="background: var(--bg-app);">
	<p style="color: var(--text-muted);">Redirecting...</p>
</div>
