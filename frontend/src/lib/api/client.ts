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
	if (res.status === 401 && !path.includes('/auth/')) {
		if (typeof window !== 'undefined') {
			localStorage.removeItem('motes_token');
			window.location.href = '/login';
		}
		throw new Error('Session expired — please log in again');
	}
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

// Thread (single-thread model)
export interface ThreadMessage {
	id: string;
	role: string;
	content: string;
	message_type: string;
	created_at: string;
}
export interface Thread {
	thread_id: string;
	messages: ThreadMessage[];
}
export const getThread = (agentId: string) =>
	api<Thread>(`/agents/${agentId}/thread`);
export const clearThread = (agentId: string) =>
	api<void>(`/agents/${agentId}/thread`, { method: 'DELETE' });

// Proactive settings
export interface ProactiveSettings {
	enabled: boolean;
	interval_minutes: number;
}
export const getProactiveSettings = () =>
	api<ProactiveSettings>('/voice/proactive-settings');
export const saveProactiveSettings = (settings: ProactiveSettings) =>
	api<ProactiveSettings>('/voice/proactive-settings', {
		method: 'POST',
		body: JSON.stringify(settings)
	});

// Conversations (legacy — kept for compatibility)
export interface Conversation {
	id: string;
	agent_id: string;
	title: string;
}
export const listConversations = (agentId: string) =>
	api<Conversation[]>(`/agents/${agentId}/conversations`);

// Messages (legacy)
export interface Message {
	id: string;
	role: string;
	content: string;
	tool_name?: string;
}
export const getMessages = (conversationId: string) =>
	api<Message[]>(`/conversations/${conversationId}/messages`);

// Approvals
export interface Approval {
	id: string;
	tool_name: string;
	arguments_json: string;
	status: string;
	created_at: string;
}
export const listApprovals = (agentId: string) => api<Approval[]>(`/agents/${agentId}/approvals`);
export const approveAction = (id: string) =>
	api<{ status: string }>(`/approvals/${id}/resolve`, { method: 'POST', body: JSON.stringify({ approved: true }) });
export const denyAction = (id: string) =>
	api<{ status: string }>(`/approvals/${id}/resolve`, { method: 'POST', body: JSON.stringify({ approved: false }) });

// Scheduled Tasks
export interface ScheduledTask {
	id: string;
	prompt: string;
	cron_expression: string;
	enabled: boolean;
	run_count: number;
	last_run_at: string | null;
}
export const listTasks = (agentId: string) => api<ScheduledTask[]>(`/agents/${agentId}/tasks`);
export const createTask = (agentId: string, data: { name: string; prompt: string; cron_expression: string }) =>
	api<ScheduledTask>(`/agents/${agentId}/tasks`, { method: 'POST', body: JSON.stringify(data) });
export const deleteTask = (agentId: string, id: string) =>
	api<void>(`/agents/${agentId}/tasks/${id}`, { method: 'DELETE' });
export const pauseTask = (agentId: string, id: string) =>
	api<ScheduledTask>(`/agents/${agentId}/tasks/${id}/pause`, { method: 'POST' });
export const resumeTask = (agentId: string, id: string) =>
	api<ScheduledTask>(`/agents/${agentId}/tasks/${id}/resume`, { method: 'POST' });

// MCP Servers
export interface McpServer {
	id: string;
	name: string;
	server_type: string;
	command_or_url: string;
	enabled: boolean;
	tools: string[];
}
export interface McpTestResult {
	connected: boolean;
	tools_count: number;
	tools: string[];
}
export const listMcpServers = () => api<McpServer[]>('/mcp/servers');
export const addMcpServer = (data: { name: string; server_type: string; command?: string; args?: string[]; url?: string }) =>
	api<McpServer>('/mcp/servers', { method: 'POST', body: JSON.stringify(data) });
export const deleteMcpServer = (id: string) =>
	api<void>(`/mcp/servers/${id}`, { method: 'DELETE' });
export const testMcpServer = (id: string) =>
	api<McpTestResult>(`/mcp/servers/${id}/test`, { method: 'POST' });

// Webhook Config (Slack / Telegram)
export const configureSlackWebhook = (data: { slack_channel_id: string; agent_id: string }) =>
	api<{ status: string }>('/webhooks/slack/config', { method: 'POST', body: JSON.stringify(data) });
export const configureTelegramWebhook = (data: { telegram_chat_id: string; agent_id: string }) =>
	api<{ status: string }>('/webhooks/telegram/config', { method: 'POST', body: JSON.stringify(data) });
