"""
Seed data migration.
Inserts default Jira templates, dev tenant, and test user.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import uuid

revision = '002_seed_data'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert seed data."""

    # ─────────────────────────────────────────────────────────────────────────
    # Create dev tenant
    # ─────────────────────────────────────────────────────────────────────────
    dev_tenant_id = str(uuid.uuid4())
    tenants_table = sa.table(
        'tenants',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.String),
        sa.column('github_org', sa.String),
        sa.column('plan', sa.String),
        sa.column('rate_limit_per_min', sa.Integer),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        tenants_table,
        [
            {
                'id': dev_tenant_id,
                'name': 'DevPulse Dev Tenant',
                'github_org': 'devpulse-dev',
                'plan': 'enterprise',
                'rate_limit_per_min': 1000,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
        ]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Create test user
    # ─────────────────────────────────────────────────────────────────────────
    users_table = sa.table(
        'users',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('tenant_id', postgresql.UUID(as_uuid=True)),
        sa.column('github_id', sa.BigInteger),
        sa.column('github_login', sa.String),
        sa.column('email', sa.String),
        sa.column('role', sa.String),
        sa.column('access_token', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        users_table,
        [
            {
                'id': str(uuid.uuid4()),
                'tenant_id': dev_tenant_id,
                'github_id': 123456789,
                'github_login': 'devpulse-test',
                'email': 'test@devpulse.io',
                'role': 'owner',
                'access_token': 'encrypted:test-token-dev',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
        ]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Create tenant settings
    # ─────────────────────────────────────────────────────────────────────────
    tenant_settings_table = sa.table(
        'tenant_settings',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('tenant_id', postgresql.UUID(as_uuid=True)),
        sa.column('analysis_window_days', sa.Integer),
        sa.column('slack_webhook_url', sa.String),
        sa.column('smtp_host', sa.String),
        sa.column('smtp_port', sa.Integer),
        sa.column('smtp_user', sa.String),
        sa.column('smtp_password', sa.String),
        sa.column('notification_email', sa.String),
        sa.column('jira_base_url', sa.String),
        sa.column('jira_api_user', sa.String),
        sa.column('jira_api_token', sa.String),
        sa.column('jira_project_key', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        tenant_settings_table,
        [
            {
                'id': str(uuid.uuid4()),
                'tenant_id': dev_tenant_id,
                'analysis_window_days': 7,
                'slack_webhook_url': None,
                'smtp_host': None,
                'smtp_port': None,
                'smtp_user': None,
                'smtp_password': None,
                'notification_email': None,
                'jira_base_url': None,
                'jira_api_user': None,
                'jira_api_token': None,
                'jira_project_key': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }
        ]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Create 3 default Jira templates (one per anomaly type)
    # ─────────────────────────────────────────────────────────────────────────
    jira_templates_table = sa.table(
        'jira_templates',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('tenant_id', postgresql.UUID(as_uuid=True)),
        sa.column('anomaly_type', sa.String),
        sa.column('summary_template', sa.String),
        sa.column('description_template', sa.Text),
        sa.column('issue_type', sa.String),
        sa.column('priority_default', sa.String),
        sa.column('labels', postgresql.JSONB(astext_type=sa.Text())),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    now = datetime.utcnow()

    op.bulk_insert(
        jira_templates_table,
        [
            {
                'id': str(uuid.uuid4()),
                'tenant_id': dev_tenant_id,
                'anomaly_type': 'burnout_risk',
                'summary_template': '[DevPulse] Burnout Risk: {developer_login} - {metric}',
                'description_template': (
                    'DevPulse detected elevated burnout signals for {developer_login}.\n\n'
                    'Metric: {metric}\n\n'
                    'Action: Consider offering support, flexible hours, or workload redistribution.'
                ),
                'issue_type': 'Task',
                'priority_default': 'High',
                'labels': '["devpulse", "engineering-health", "burnout-risk"]',
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': dev_tenant_id,
                'anomaly_type': 'high_churn',
                'summary_template': '[DevPulse] High Code Churn: {developer_login} - {metric}',
                'description_template': (
                    'DevPulse detected high code churn from {developer_login}.\n\n'
                    'Metric: {metric}\n\n'
                    'Action: Review commits for complexity, refactoring scope, or migration work.'
                ),
                'issue_type': 'Task',
                'priority_default': 'Medium',
                'labels': '["devpulse", "engineering-health", "code-quality"]',
                'created_at': now,
                'updated_at': now,
            },
            {
                'id': str(uuid.uuid4()),
                'tenant_id': dev_tenant_id,
                'anomaly_type': 'slow_review',
                'summary_template': '[DevPulse] Slow Review Cycle: {developer_login} - {metric}',
                'description_template': (
                    'DevPulse detected slow PR review cycle for {developer_login}.\n\n'
                    'Metric: {metric}\n\n'
                    'Action: Check if reviewer availability is the issue or if PR quality is holding things up.'
                ),
                'issue_type': 'Task',
                'priority_default': 'Medium',
                'labels': '["devpulse", "engineering-health", "review-process"]',
                'created_at': now,
                'updated_at': now,
            }
        ]
    )


def downgrade() -> None:
    """Delete seed data."""

    # Delete in reverse order
    op.execute("DELETE FROM jira_templates WHERE tenant_id = (SELECT id FROM tenants WHERE github_org = 'devpulse-dev')")
    op.execute("DELETE FROM tenant_settings WHERE tenant_id = (SELECT id FROM tenants WHERE github_org = 'devpulse-dev')")
    op.execute("DELETE FROM users WHERE tenant_id = (SELECT id FROM tenants WHERE github_org = 'devpulse-dev')")
    op.execute("DELETE FROM tenants WHERE github_org = 'devpulse-dev'")
