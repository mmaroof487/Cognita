"""
Initial schema creation migration.
Creates all tables with proper indices, constraints, and TimescaleDB hypertables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""

    # Enable TimescaleDB extension
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb')

    # ─────────────────────────────────────────────────────────────────────────
    # TENANTS (multi-tenancy anchor)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('github_org', sa.String(255), nullable=False, unique=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='free'),
        sa.Column('rate_limit_per_min', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_tenants_plan', 'tenants', ['plan'])

    # ─────────────────────────────────────────────────────────────────────────
    # USERS (authenticated users per tenant)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('github_login', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('access_token', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'github_id', name='uq_users_tenant_github_id'),
    )
    op.create_index('idx_users_tenant', 'users', ['tenant_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # ORGS (GitHub orgs per tenant)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'orgs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_org', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'github_org', name='uq_orgs_tenant_github_org'),
    )
    op.create_index('idx_orgs_tenant', 'orgs', ['tenant_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # REPOS
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'repos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(500), nullable=False),
        sa.Column('private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tracked', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'github_id', name='uq_repos_tenant_github_id'),
    )
    op.create_index('idx_repos_tenant', 'repos', ['tenant_id'])
    op.create_index('idx_repos_org', 'repos', ['org_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # DEVELOPERS (tracked contributors)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'developers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_login', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'github_login', name='uq_developers_tenant_login'),
    )
    op.create_index('idx_developers_tenant', 'developers', ['tenant_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # COMMIT_EVENTS (time-series, can be compressed by TimescaleDB)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'commit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('developer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sha', sa.String(40), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('additions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deletions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('files_changed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['developer_id'], ['developers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', 'committed_at'),
        sa.UniqueConstraint('tenant_id', 'sha', 'committed_at', name='uq_commits_tenant_sha'),
    )
    op.create_index('idx_commits_developer_time', 'commit_events', ['developer_id', 'committed_at'])
    op.create_index('idx_commits_tenant', 'commit_events', ['tenant_id'])
    op.create_index('idx_commits_repo', 'commit_events', ['repo_id'])

    # Make commit_events a hypertable (TimescaleDB) for time-series compression
    op.execute('SELECT create_hypertable(\'commit_events\', \'committed_at\', if_not_exists => TRUE);')

    # ─────────────────────────────────────────────────────────────────────────
    # PR_EVENTS
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'pr_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repo_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_pr_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('additions', sa.Integer(), nullable=True),
        sa.Column('deletions', sa.Integer(), nullable=True),
        sa.Column('review_comments', sa.Integer(), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_to_merge_h', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['developers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'github_pr_id', name='uq_prs_tenant_github_id'),
    )
    op.create_index('idx_prs_tenant', 'pr_events', ['tenant_id'])
    op.create_index('idx_prs_repo', 'pr_events', ['repo_id'])
    op.create_index('idx_prs_author', 'pr_events', ['author_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT_RUNS (LangGraph execution tracking)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'agent_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', sa.String(255), nullable=False, unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('triggered_by', sa.String(50), nullable=False, server_default='schedule'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_agent_runs_tenant_started', 'agent_runs', ['tenant_id', 'started_at'])
    op.create_index('idx_agent_runs_status', 'agent_runs', ['status'])

    # ─────────────────────────────────────────────────────────────────────────
    # INSIGHTS (agent-generated findings)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('developer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('insight_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False, server_default='info'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['developer_id'], ['developers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_insights_tenant_run', 'insights', ['tenant_id', 'agent_run_id'])
    op.create_index('idx_insights_developer', 'insights', ['developer_id'])
    op.create_index('idx_insights_severity', 'insights', ['severity'])

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT_ACTIONS (HITL gate)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'agent_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insight_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['insight_id'], ['insights.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_agent_actions_tenant', 'agent_actions', ['tenant_id'])
    op.create_index('idx_agent_actions_status', 'agent_actions', ['status'])
    op.create_index('idx_agent_actions_reviewed', 'agent_actions', ['reviewed_by'])

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT_LOG (immutable append-only log)
    # ─────────────────────────────────────────────────────────────────────────
    op.execute('''
        CREATE TABLE audit_log (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id UUID,
            diff JSONB,
            ts TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    op.create_index('idx_audit_log_tenant', 'audit_log', ['tenant_id'])
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])

    # Prevent updates/deletes on audit log
    op.execute('CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING')
    op.execute('CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING')

    # ─────────────────────────────────────────────────────────────────────────
    # TENANT_SETTINGS (notification config per tenant)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'tenant_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('analysis_window_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('slack_webhook_url', sa.String(1000), nullable=True),
        sa.Column('smtp_host', sa.String(255), nullable=True),
        sa.Column('smtp_port', sa.Integer(), nullable=True),
        sa.Column('smtp_user', sa.String(255), nullable=True),
        sa.Column('smtp_password', sa.String(500), nullable=True),
        sa.Column('notification_email', sa.String(255), nullable=True),
        sa.Column('jira_base_url', sa.String(500), nullable=True),
        sa.Column('jira_api_user', sa.String(255), nullable=True),
        sa.Column('jira_api_token', sa.String(500), nullable=True),
        sa.Column('jira_project_key', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_tenant_settings_tenant', 'tenant_settings', ['tenant_id'])

    # ─────────────────────────────────────────────────────────────────────────
    # JIRA_TEMPLATES (per-tenant, one per anomaly type)
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'jira_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('anomaly_type', sa.String(100), nullable=False),
        sa.Column('summary_template', sa.String(500), nullable=False),
        sa.Column('description_template', sa.Text(), nullable=False),
        sa.Column('issue_type', sa.String(100), nullable=False, server_default='Task'),
        sa.Column('priority_default', sa.String(50), nullable=False, server_default='Medium'),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_jira_templates_tenant', 'jira_templates', ['tenant_id'])
    op.create_index('idx_jira_templates_type', 'jira_templates', ['anomaly_type'])


def downgrade() -> None:
    """Drop all tables (reverse)."""

    # Drop tables in reverse dependency order
    op.drop_table('jira_templates')
    op.drop_table('tenant_settings')
    op.execute('DROP TABLE IF EXISTS audit_log')
    op.drop_table('agent_actions')
    op.drop_table('insights')
    op.drop_table('agent_runs')
    op.drop_table('pr_events')
    op.drop_table('commit_events')
    op.drop_table('developers')
    op.drop_table('repos')
    op.drop_table('orgs')
    op.drop_table('users')
    op.drop_table('tenants')
