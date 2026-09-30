/**
 * Theme store — dark/light mode toggle.
 */
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function getInitialTheme(): 'dark' | 'light' {
	if (!browser) return 'dark';
	const saved = localStorage.getItem('motes_theme');
	if (saved === 'light' || saved === 'dark') return saved;
	return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export const theme = writable<'dark' | 'light'>(getInitialTheme());

export function toggleTheme() {
	theme.update((t) => {
		const next = t === 'dark' ? 'light' : 'dark';
		if (browser) {
			localStorage.setItem('motes_theme', next);
			document.documentElement.classList.toggle('dark', next === 'dark');
		}
		return next;
	});
}

// Apply on load
if (browser) {
	const initial = getInitialTheme();
	document.documentElement.classList.toggle('dark', initial === 'dark');
}
