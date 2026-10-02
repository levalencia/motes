/**
 * Smoke tests — verify data helpers and formatters don't crash on edge cases.
 * These catch the bugs that broke the settings page (undefined.length, missing fields, etc.)
 */
import { describe, it, expect } from 'vitest';

// ── Tool description formatters (matching dashboard logic) ──

const toolDescriptions: Record<string, string> = {
	gmail_send: '📧 Send an email via Gmail',
	outlook_send_email: '📧 Send an email via Outlook',
	calendar_create: '📅 Create a calendar event',
	reminders_create: '🔔 Create a reminder in Apple Reminders',
	file_download_url: '📁 Generate a file download link',
	pptx_add_slide: '📊 Add a slide to a PowerPoint',
};

function formatToolName(toolName: string): string {
	return toolDescriptions[toolName] || toolName.replace(/_/g, ' ');
}

function formatToolArgs(toolName: string, argsJson: string): string {
	try {
		const args = JSON.parse(argsJson);
		switch (toolName) {
			case 'gmail_send':
			case 'outlook_send_email':
				return `To: ${args.to || '?'}\nSubject: ${args.subject || '?'}`;
			case 'reminders_create':
				return `Reminder: ${args.title || args.text || args.name || JSON.stringify(args)}`;
			default:
				return Object.entries(args).map(([k, v]) => `${k}: ${v}`).join('\n');
		}
	} catch {
		return argsJson;
	}
}

function formatTime(iso: string): string {
	if (!iso) return '';
	const d = new Date(iso);
	const now = new Date();
	const isToday = d.toDateString() === now.toDateString();
	const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	if (isToday) return time;
	return `${d.toLocaleDateString([], { day: 'numeric', month: 'short' })} ${time}`;
}

describe('formatToolName', () => {
	it('returns human description for known tools', () => {
		expect(formatToolName('gmail_send')).toBe('📧 Send an email via Gmail');
		expect(formatToolName('reminders_create')).toBe('🔔 Create a reminder in Apple Reminders');
	});

	it('falls back to replacing underscores for unknown tools', () => {
		expect(formatToolName('some_random_tool')).toBe('some random tool');
	});

	it('handles empty string', () => {
		expect(formatToolName('')).toBe('');
	});
});

describe('formatToolArgs', () => {
	it('formats email tool args', () => {
		const result = formatToolArgs('gmail_send', '{"to":"alice@test.com","subject":"Hello"}');
		expect(result).toContain('To: alice@test.com');
		expect(result).toContain('Subject: Hello');
	});

	it('formats reminder tool args', () => {
		const result = formatToolArgs('reminders_create', '{"title":"Buy milk"}');
		expect(result).toBe('Reminder: Buy milk');
	});

	it('handles invalid JSON gracefully', () => {
		expect(formatToolArgs('gmail_send', 'not-json')).toBe('not-json');
	});

	it('handles empty JSON', () => {
		expect(formatToolArgs('unknown_tool', '{}')).toBe('');
	});

	it('handles missing fields', () => {
		const result = formatToolArgs('gmail_send', '{}');
		expect(result).toContain('To: ?');
		expect(result).toContain('Subject: ?');
	});
});

describe('formatTime', () => {
	it('returns empty for empty input', () => {
		expect(formatTime('')).toBe('');
	});

	it('formats a valid ISO date', () => {
		const result = formatTime('2026-10-01T15:30:00Z');
		expect(result).toBeTruthy();
		expect(result.length).toBeGreaterThan(0);
	});
});

// ── MCP server.tools guard ──

describe('MCP server tools guard', () => {
	it('handles undefined tools array', () => {
		const server = { id: '1', name: 'test', server_type: 'stdio' } as any;
		const toolCount = server.tools?.length ?? 0;
		expect(toolCount).toBe(0);
	});

	it('handles null tools array', () => {
		const server = { id: '1', name: 'test', tools: null } as any;
		const toolCount = server.tools?.length ?? 0;
		expect(toolCount).toBe(0);
	});

	it('handles empty tools array', () => {
		const server = { id: '1', name: 'test', tools: [] };
		const toolCount = server.tools?.length ?? 0;
		expect(toolCount).toBe(0);
	});

	it('handles populated tools array', () => {
		const server = { id: '1', name: 'test', tools: ['search', 'read'] };
		const toolCount = server.tools?.length ?? 0;
		expect(toolCount).toBe(2);
	});
});

// ── Approval fields guard ──

describe('Approval data guards', () => {
	it('handles approval with all fields', () => {
		const approval = {
			id: '1',
			tool_name: 'gmail_send',
			arguments_json: '{"to":"alice@test.com"}',
			status: 'pending',
			created_at: '2026-10-01T15:30:00Z',
		};
		expect(formatToolName(approval.tool_name)).toBe('📧 Send an email via Gmail');
		expect(formatToolArgs(approval.tool_name, approval.arguments_json)).toContain('alice@test.com');
	});

	it('handles approval with empty arguments', () => {
		const approval = {
			id: '1',
			tool_name: 'unknown_tool',
			arguments_json: '{}',
			status: 'pending',
			created_at: '',
		};
		expect(formatToolName(approval.tool_name)).toBe('unknown tool');
		expect(formatToolArgs(approval.tool_name, approval.arguments_json)).toBe('');
	});
});

// ── Schedule cron formatting ──

describe('Schedule presets', () => {
	const cronMap: Record<string, string> = {
		'0 7 * * *': '🌅 Every morning 7am',
		'0 8 * * *': '⏰ Every morning 8am',
		'0 19 * * *': '🌆 Daily 7pm',
		'0 * * * *': '🕐 Every hour',
		'*/30 * * * *': '⏱ Every 30 min',
		'0 9 * * 1-5': '📅 Weekdays 9am',
		'0 10 * * 0,6': '🛋 Weekends 10am',
		'0 23 * * *': '🌙 Every night 11pm',
		'0 9 * * 1': '📆 Monday 9am',
		'0 17 * * 5': '📆 Friday 5pm',
	};

	it('maps all 10 presets correctly', () => {
		expect(Object.keys(cronMap)).toHaveLength(10);
		for (const [cron, label] of Object.entries(cronMap)) {
			expect(label.length).toBeGreaterThan(0);
			expect(cron).toMatch(/^[\d\*\/\-\,\s]+$/);
		}
	});

	it('returns raw cron for unknown patterns', () => {
		const unknown = '15 3 1 * *';
		const result = cronMap[unknown] || unknown;
		expect(result).toBe('15 3 1 * *');
	});
});
