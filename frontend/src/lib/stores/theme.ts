/**
 * Theme store — dark/light mode toggle.
 */
import { writable } from 'svelte/store';

const stored = typeof window !== 'undefined' ? localStorage.getItem('motes_theme') : null;

export const theme = writable<'dark' | 'light'>((stored as 'dark' | 'light') || 'dark');

export function toggleTheme() {
	theme.update((t) => {
		const next = t === 'dark' ? 'light' : 'dark';
		if (typeof window !== 'undefined') {
			localStorage.setItem('motes_theme', next);
			document.documentElement.setAttribute('data-theme', next);
		}
		return next;
	});
}

export function initTheme() {
	if (typeof window !== 'undefined') {
		const saved = localStorage.getItem('motes_theme') as 'dark' | 'light' | null;
		const t = saved || 'dark';
		document.documentElement.setAttribute('data-theme', t);
		theme.set(t);
	}
}
