"""add approvals, scheduler, proactive, memory, mcp, oauth, voice, settings tables

Revision ID: a2f4c8e91d03
Revises: b1302d3b0ee7
Create Date: 2026-10-02 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a2f4c8e91d03'
down_revision: str | Sequence[str] | None = 'b1302d3b0ee7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add all new tables for approvals, scheduler, proactive, memory, etc."""

    # ── User columns added since initial migration ──
    op.add_column('users', sa.Column('voice_personality', sa.String(), nullable=False, server_default=''))
    op.add_column('users', sa.Column('proactive_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('users', sa.Column(
        'proactive_interval_minutes', sa.Integer(), nullable=False, server_default=sa.text('60'),
    ))
    op.add_column('users', sa.Column(
        'scan_interval_seconds', sa.Integer(), nullable=False, server_default=sa.text('60'),
    ))

    # ── Conversation columns ──
    op.add_column('conversations', sa.Column('conversation_type', sa.String(), nullable=False, server_default='chat'))
    op.add_column('conversations', sa.Column(
        'updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False,
    ))

    # ── Message columns ──
    op.add_column('messages', sa.Column('message_type', sa.String(), nullable=False, server_default='chat'))

    # ── Provider columns ──
    op.add_column('providers', sa.Column('api_format', sa.String(), nullable=False, server_default='openai'))

    # ── App Settings ──
    op.create_table('app_settings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_app_settings_key'), 'app_settings', ['key'], unique=True)

    # ── Memories ──
    op.create_table('memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_memories_agent_id'), 'memories', ['agent_id'], unique=False)
    op.create_index(op.f('ix_memories_category'), 'memories', ['category'], unique=False)

    # ── Approval Policies ──
    op.create_table('approval_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('risk_level', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_approval_policies_agent_id'), 'approval_policies', ['agent_id'], unique=False)
    op.create_index(op.f('ix_approval_policies_tool_name'), 'approval_policies', ['tool_name'], unique=False)

    # ── Approval Requests ──
    op.create_table('approval_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('arguments_json', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_approval_requests_agent_id'), 'approval_requests', ['agent_id'], unique=False)
    op.create_index(op.f('ix_approval_requests_status'), 'approval_requests', ['status'], unique=False)

    # ── Scheduled Tasks ──
    op.create_table('scheduled_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('cron_expression', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('max_runs', sa.Integer(), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scheduled_tasks_agent_id'), 'scheduled_tasks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_scheduled_tasks_status'), 'scheduled_tasks', ['status'], unique=False)

    # ── Task Runs ──
    op.create_table('task_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['scheduled_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_task_runs_task_id'), 'task_runs', ['task_id'], unique=False)

    # ── User Patterns (proactive) ──
    op.create_table('user_patterns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=False),
        sa.Column('pattern_key', sa.String(), nullable=False),
        sa.Column('pattern_data', sa.Text(), nullable=False),
        sa.Column('frequency', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_patterns_agent_id'), 'user_patterns', ['agent_id'], unique=False)
    op.create_index(op.f('ix_user_patterns_pattern_type'), 'user_patterns', ['pattern_type'], unique=False)
    op.create_index(op.f('ix_user_patterns_user_id'), 'user_patterns', ['user_id'], unique=False)

    # ── Notifications ──
    op.create_table('notifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('action_url', sa.String(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_agent_id'), 'notifications', ['agent_id'], unique=False)
    op.create_index(op.f('ix_notifications_category'), 'notifications', ['category'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # ── MCP Servers ──
    op.create_table('mcp_servers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('transport', sa.String(), nullable=False),
        sa.Column('command', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('env_json', sa.Text(), nullable=False),
        sa.Column('agent_ids_json', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mcp_servers_user_id'), 'mcp_servers', ['user_id'], unique=False)

    # ── OAuth Apps ──
    op.create_table('oauth_apps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('client_secret_encrypted', sa.String(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('extra_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_oauth_apps_provider'), 'oauth_apps', ['provider'], unique=True)

    # ── OAuth Tokens ──
    op.create_table('oauth_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('access_token_encrypted', sa.String(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.String(), nullable=False),
        sa.Column('token_type', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('account_email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_oauth_tokens_provider'), 'oauth_tokens', ['provider'], unique=False)
    op.create_index(op.f('ix_oauth_tokens_user_id'), 'oauth_tokens', ['user_id'], unique=False)

    # ── Voice Providers ──
    op.create_table('voice_providers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('capability', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=False),
        sa.Column('api_key_encrypted', sa.String(), nullable=False),
        sa.Column('stt_model', sa.String(), nullable=False),
        sa.Column('tts_model', sa.String(), nullable=False),
        sa.Column('tts_voice', sa.String(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_voice_providers_user_id'), 'voice_providers', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove all tables added by this migration."""
    op.drop_index(op.f('ix_voice_providers_user_id'), table_name='voice_providers')
    op.drop_table('voice_providers')
    op.drop_index(op.f('ix_oauth_tokens_user_id'), table_name='oauth_tokens')
    op.drop_index(op.f('ix_oauth_tokens_provider'), table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
    op.drop_index(op.f('ix_oauth_apps_provider'), table_name='oauth_apps')
    op.drop_table('oauth_apps')
    op.drop_index(op.f('ix_mcp_servers_user_id'), table_name='mcp_servers')
    op.drop_table('mcp_servers')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_category'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_agent_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_user_patterns_user_id'), table_name='user_patterns')
    op.drop_index(op.f('ix_user_patterns_pattern_type'), table_name='user_patterns')
    op.drop_index(op.f('ix_user_patterns_agent_id'), table_name='user_patterns')
    op.drop_table('user_patterns')
    op.drop_index(op.f('ix_task_runs_task_id'), table_name='task_runs')
    op.drop_table('task_runs')
    op.drop_index(op.f('ix_scheduled_tasks_status'), table_name='scheduled_tasks')
    op.drop_index(op.f('ix_scheduled_tasks_agent_id'), table_name='scheduled_tasks')
    op.drop_table('scheduled_tasks')
    op.drop_index(op.f('ix_approval_requests_status'), table_name='approval_requests')
    op.drop_index(op.f('ix_approval_requests_agent_id'), table_name='approval_requests')
    op.drop_table('approval_requests')
    op.drop_index(op.f('ix_approval_policies_tool_name'), table_name='approval_policies')
    op.drop_index(op.f('ix_approval_policies_agent_id'), table_name='approval_policies')
    op.drop_table('approval_policies')
    op.drop_index(op.f('ix_memories_category'), table_name='memories')
    op.drop_index(op.f('ix_memories_agent_id'), table_name='memories')
    op.drop_table('memories')
    op.drop_index(op.f('ix_app_settings_key'), table_name='app_settings')
    op.drop_table('app_settings')

    # Remove added columns
    op.drop_column('providers', 'api_format')
    op.drop_column('messages', 'message_type')
    op.drop_column('conversations', 'updated_at')
    op.drop_column('conversations', 'conversation_type')
    op.drop_column('users', 'scan_interval_seconds')
    op.drop_column('users', 'proactive_interval_minutes')
    op.drop_column('users', 'proactive_enabled')
    op.drop_column('users', 'voice_personality')
