/**
 * Auth store — manages token and user state.
 */
import { writable, derived } from 'svelte/store';

export const token = writable<string | null>(
	typeof window !== 'undefined' ? localStorage.getItem('motes_token') : null
);
export const username = writable<string | null>(
	typeof window !== 'undefined' ? localStorage.getItem('motes_username') : null
);

export const isAuthenticated = derived(token, ($token) => !!$token);

export function setAuth(t: string, u: string) {
	token.set(t);
	username.set(u);
	if (typeof window !== 'undefined') {
		localStorage.setItem('motes_token', t);
		localStorage.setItem('motes_username', u);
	}
}

export function clearAuth() {
	token.set(null);
	username.set(null);
	if (typeof window !== 'undefined') {
		localStorage.removeItem('motes_token');
		localStorage.removeItem('motes_username');
	}
}
