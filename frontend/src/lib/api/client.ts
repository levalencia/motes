/**
 * API client for Motes backend.
 */

const API_BASE = 'http://localhost:8001/api';

function getHeaders(): Record<string, string> {
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	if (typeof window !== 'undefined') {
		const token = localStorage.getItem('motes_token');
		if (token) headers['Authorization'] = `Bearer ${token}`;
	}
	return headers;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		...options,
		headers: { ...getHeaders(), ...(options.headers || {}) }
	});
	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(body.detail || `HTTP ${res.status}`);
	}
	return res.json();
}

// Auth
export const checkSetup = () => api<{ is_setup_complete: boolean }>('/auth/setup-status');
export const setup = (username: string, password: string) =>
	api<{ token: string; user_id: string; username: string }>('/auth/setup', {
		method: 'POST',
		body: JSON.stringify({ username, password })
	});
export const login = (username: string, password: string) =>
	api<{ token: string; user_id: string; username: string }>('/auth/login', {
		method: 'POST',
		body: JSON.stringify({ username, password })
	});

// Providers
export interface Provider {
	id: string;
	name: string;
	base_url: string;
	model: string;
	is_verified: boolean;
}
export const listProviders = () => api<Provider[]>('/providers');
export const createProvider = (data: { name: string; base_url: string; api_key: string; model: string }) =>
	api<Provider>('/providers', { method: 'POST', body: JSON.stringify(data) });
export const deleteProvider = (id: string) =>
	api<void>(`/providers/${id}`, { method: 'DELETE' });

// Agents
export interface Agent {
	id: string;
	name: string;
	provider_id: string;
	system_prompt: string;
	provider_name?: string;
	model?: string;
}
export const listAgents = () => api<Agent[]>('/agents');
export const createAgent = (data: { name: string; provider_id: string; system_prompt?: string }) =>
	api<Agent>('/agents', { method: 'POST', body: JSON.stringify(data) });
export const deleteAgent = (id: string) =>
	api<void>(`/agents/${id}`, { method: 'DELETE' });

// Conversations
export interface Conversation {
	id: string;
	agent_id: string;
	title: string;
}
export const listConversations = (agentId: string) =>
	api<Conversation[]>(`/agents/${agentId}/conversations`);

// Messages
export interface Message {
	id: string;
	role: string;
	content: string;
	tool_name?: string;
}
export const getMessages = (conversationId: string) =>
	api<Message[]>(`/conversations/${conversationId}/messages`);
