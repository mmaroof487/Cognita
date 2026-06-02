"""
Seed data migration.
Inserts default Jira templates, dev tenant, and test user.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.models import Tenant, User, TenantSettings, JiraTemplate
from app.core.security import fernet_encrypt

revision = '002_seed_data'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Insert seed data using ORM."""
    bind = op.get_bind()
    session = Session(bind=bind)

    dev_tenant_id = uuid.uuid4()
    dev_tenant = Tenant(
        id=dev_tenant_id,
        name='DevPulse Dev Tenant',
        github_org='devpulse-dev',
        plan='enterprise',
        rate_limit_per_min=1000
    )
    session.add(dev_tenant)

    test_user = User(
        id=uuid.uuid4(),
        tenant_id=dev_tenant_id,
        github_id=123456789,
        github_login='devpulse-test',
        email='test@devpulse.io',
        role='owner',
        access_token=fernet_encrypt('test-token-dev')
    )
    session.add(test_user)

    settings = TenantSettings(
        id=uuid.uuid4(),
        tenant_id=dev_tenant_id,
        analysis_window_days=7
    )
    session.add(settings)

    templates = [
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=dev_tenant_id,
            anomaly_type='burnout_risk',
            summary_template='[DevPulse] Burnout Risk: {developer_login} - {metric}',
            description_template='DevPulse detected elevated burnout signals for {developer_login}.\n\nMetric: {metric}\n\nAction: Consider offering support, flexible hours, or workload redistribution.',
            issue_type='Task',
            priority_default='High',
            labels=["devpulse", "engineering-health", "burnout-risk"]
        ),
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=dev_tenant_id,
            anomaly_type='high_churn',
            summary_template='[DevPulse] High Code Churn: {developer_login} - {metric}',
            description_template='DevPulse detected high code churn from {developer_login}.\n\nMetric: {metric}\n\nAction: Review commits for complexity, refactoring scope, or migration work.',
            issue_type='Task',
            priority_default='Medium',
            labels=["devpulse", "engineering-health", "code-quality"]
        ),
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=dev_tenant_id,
            anomaly_type='slow_review',
            summary_template='[DevPulse] Slow Review Cycle: {developer_login} - {metric}',
            description_template='DevPulse detected slow PR review cycle for {developer_login}.\n\nMetric: {metric}\n\nAction: Check if reviewer availability is the issue or if PR quality is holding things up.',
            issue_type='Task',
            priority_default='Medium',
            labels=["devpulse", "engineering-health", "review-process"]
        )
    ]
    session.add_all(templates)
    
    session.commit()

def downgrade() -> None:
    """Delete seed data using ORM."""
    bind = op.get_bind()
    session = Session(bind=bind)
    
    tenant = session.query(Tenant).filter_by(github_org='devpulse-dev').first()
    if tenant:
        session.query(JiraTemplate).filter_by(tenant_id=tenant.id).delete()
        session.query(TenantSettings).filter_by(tenant_id=tenant.id).delete()
        session.query(User).filter_by(tenant_id=tenant.id).delete()
        session.delete(tenant)
        session.commit()

