<script lang="ts">
	import '../app.css';
	import { theme, toggleTheme } from '$lib/stores/theme';
	let { children } = $props();
</script>

<div class={$theme === 'dark' ? 'dark' : ''}>
	{@render children()}
</div>
