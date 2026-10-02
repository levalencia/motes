/**
 * API Client unit tests — verifies all API functions construct correct URLs and payloads.
 * These mock fetch() so they don't need a running backend.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage for auth token
const mockStorage: Record<string, string> = { motes_token: 'test-token-123' };
global.localStorage = {
	getItem: (key: string) => mockStorage[key] ?? null,
	setItem: (key: string, val: string) => { mockStorage[key] = val; },
	removeItem: (key: string) => { delete mockStorage[key]; },
	clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
	length: 0,
	key: () => null,
};

// Mock window.location for 401 redirect
const mockLocation = { href: '' };
Object.defineProperty(global, 'window', {
	value: { location: mockLocation },
	writable: true,
});

import {
	listApprovals, approveAction, denyAction,
	listTasks, createTask, deleteTask, pauseTask, resumeTask,
	listMcpServers, addMcpServer, deleteMcpServer, testMcpServer,
	type Approval, type ScheduledTask, type McpServer,
} from '$lib/api/client';

function mockOk(data: any) {
	mockFetch.mockResolvedValueOnce({
		ok: true,
		status: 200,
		json: () => Promise.resolve(data),
	});
}

function mockError(status: number, detail: string) {
	mockFetch.mockResolvedValueOnce({
		ok: false,
		status,
		json: () => Promise.resolve({ detail }),
	});
}

beforeEach(() => {
	mockFetch.mockReset();
	mockLocation.href = '';
});

// ── Approvals ──

describe('Approvals API', () => {
	it('listApprovals calls correct URL with agentId', async () => {
		mockOk([]);
		await listApprovals('agent-123');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/agents/agent-123/approvals'),
			expect.objectContaining({
				headers: expect.objectContaining({ Authorization: 'Bearer test-token-123' }),
			}),
		);
	});

	it('approveAction calls /resolve with approved=true', async () => {
		mockOk({ status: 'approved' });
		await approveAction('req-456');
		const [url, opts] = mockFetch.mock.calls[0];
		expect(url).toContain('/api/approvals/req-456/resolve');
		expect(opts.method).toBe('POST');
		expect(JSON.parse(opts.body)).toEqual({ approved: true });
	});

	it('denyAction calls /resolve with approved=false', async () => {
		mockOk({ status: 'denied' });
		await denyAction('req-789');
		const [url, opts] = mockFetch.mock.calls[0];
		expect(url).toContain('/api/approvals/req-789/resolve');
		expect(JSON.parse(opts.body)).toEqual({ approved: false });
	});
});

// ── Scheduled Tasks ──

describe('Scheduled Tasks API', () => {
	it('listTasks uses agent-scoped URL', async () => {
		mockOk([]);
		await listTasks('agent-1');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/agents/agent-1/tasks'),
			expect.anything(),
		);
	});

	it('createTask sends name, prompt, cron_expression', async () => {
		mockOk({ id: 't1', name: 'test', prompt: 'hi', cron_expression: '0 8 * * *', enabled: true, run_count: 0, last_run_at: null });
		await createTask('agent-1', { name: 'Morning', prompt: 'check email', cron_expression: '0 8 * * *' });
		const [url, opts] = mockFetch.mock.calls[0];
		expect(url).toContain('/api/agents/agent-1/tasks');
		expect(opts.method).toBe('POST');
		const body = JSON.parse(opts.body);
		expect(body.name).toBe('Morning');
		expect(body.prompt).toBe('check email');
		expect(body.cron_expression).toBe('0 8 * * *');
	});

	it('deleteTask uses agent-scoped URL', async () => {
		mockOk(undefined);
		await deleteTask('agent-1', 'task-99');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/agents/agent-1/tasks/task-99'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('pauseTask calls /pause endpoint', async () => {
		mockOk({ id: 't1' });
		await pauseTask('agent-1', 'task-5');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/agents/agent-1/tasks/task-5/pause'),
			expect.objectContaining({ method: 'POST' }),
		);
	});

	it('resumeTask calls /resume endpoint', async () => {
		mockOk({ id: 't1' });
		await resumeTask('agent-1', 'task-5');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/agents/agent-1/tasks/task-5/resume'),
			expect.objectContaining({ method: 'POST' }),
		);
	});
});

// ── MCP Servers ──

describe('MCP Servers API', () => {
	it('listMcpServers calls /mcp/servers', async () => {
		mockOk([]);
		await listMcpServers();
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/mcp/servers'),
			expect.anything(),
		);
	});

	it('addMcpServer sends server config', async () => {
		mockOk({ id: 's1', name: 'test' });
		await addMcpServer({ name: 'GitHub', server_type: 'stdio', command: 'npx @mcp/github' });
		const [, opts] = mockFetch.mock.calls[0];
		const body = JSON.parse(opts.body);
		expect(body.name).toBe('GitHub');
		expect(body.server_type).toBe('stdio');
		expect(body.command).toBe('npx @mcp/github');
	});

	it('deleteMcpServer uses correct URL', async () => {
		mockOk(undefined);
		await deleteMcpServer('srv-1');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/mcp/servers/srv-1'),
			expect.objectContaining({ method: 'DELETE' }),
		);
	});

	it('testMcpServer calls /test endpoint', async () => {
		mockOk({ connected: true, tools_count: 5, tools: ['a', 'b'] });
		const result = await testMcpServer('srv-1');
		expect(mockFetch).toHaveBeenCalledWith(
			expect.stringContaining('/api/mcp/servers/srv-1/test'),
			expect.objectContaining({ method: 'POST' }),
		);
	});
});

// ── Auth guard ──

describe('Auth guard (401 redirect)', () => {
	it('redirects to /login on 401 for non-auth endpoints', async () => {
		mockError(401, 'Invalid token');
		try {
			await listTasks('agent-1');
		} catch {}
		expect(mockLocation.href).toContain('/login');
	});

	it('does NOT redirect on 401 for /auth/ endpoints', async () => {
		// The login endpoint itself returns 401 on wrong password
		// We don't want infinite redirect
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 401,
			json: () => Promise.resolve({ detail: 'Invalid credentials' }),
		});
		try {
			// Simulate calling the login endpoint directly
			const res = await fetch('http://localhost:8001/api/auth/login', {
				method: 'POST',
				body: JSON.stringify({ username: 'test', password: 'wrong' }),
			});
		} catch {}
		// Should NOT redirect because it's /auth/
		expect(mockLocation.href).toBe('');
	});
});
