"""
Tests for database schema and ORM models.
Validates table structure, columns, constraints, etc.
"""

import pytest
from sqlalchemy import inspect
from app.models import (
    Tenant, User, Org, Repo, Developer,
    CommitEvent, PrEvent, Insight, AgentRun,
    AgentAction, TenantSettings, JiraTemplate
)


@pytest.mark.asyncio
async def test_tenant_table_exists(test_session):
    """Verify tenants table exists with correct columns."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "tenants" in tables

        columns_info = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns("tenants"))
        columns = {col["name"] for col in columns_info}
        assert {"id", "name", "github_org", "plan", "rate_limit_per_min", "created_at", "updated_at"}.issubset(columns)


@pytest.mark.asyncio
async def test_user_table_exists(test_session):
    """Verify users table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "users" in tables

        columns_info = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns("users"))
        columns = {col["name"] for col in columns_info}
        assert {"id", "tenant_id", "github_id", "github_login", "email", "role", "access_token"}.issubset(columns)


@pytest.mark.asyncio
async def test_developer_table_exists(test_session):
    """Verify developers table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "developers" in tables


@pytest.mark.asyncio
async def test_commit_events_table_exists(test_session):
    """Verify commit_events table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "commit_events" in tables


@pytest.mark.asyncio
async def test_agent_runs_table_exists(test_session):
    """Verify agent_runs table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "agent_runs" in tables


@pytest.mark.asyncio
async def test_insights_table_exists(test_session):
    """Verify insights table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "insights" in tables


@pytest.mark.asyncio
async def test_audit_log_table_exists(test_session):
    """Verify audit_log table exists."""
    async with test_session.bind.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "audit_log" in tables


@pytest.mark.asyncio
async def test_tenant_unique_constraint(test_tenant, test_session):
    """Verify tenant github_org is unique."""
    async with test_session.bind.connect() as conn:
        constraints = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_unique_constraints("tenants"))
        # Should have a unique constraint on github_org
        assert any("github_org" in str(c) for c in constraints)


@pytest.mark.asyncio
async def test_tenant_creation(test_tenant):
    """Verify test tenant was created correctly."""
    assert test_tenant.id is not None
    assert test_tenant.name == "Test Tenant"
    assert test_tenant.github_org == "test-org"
    assert test_tenant.plan == "enterprise"
    assert test_tenant.rate_limit_per_min == 1000


@pytest.mark.asyncio
async def test_user_creation(test_user, test_tenant):
    """Verify test user was created correctly."""
    assert test_user.id is not None
    assert test_user.tenant_id == test_tenant.id
    assert test_user.github_login == "test-user"
    assert test_user.role == "owner"


@pytest.mark.asyncio
async def test_jira_template_creation(test_jira_templates, test_tenant):
    """Verify Jira templates were created."""
    assert len(test_jira_templates) == 3
    assert all(t.tenant_id == test_tenant.id for t in test_jira_templates)

    anomaly_types = {t.anomaly_type for t in test_jira_templates}
    assert anomaly_types == {"burnout_risk", "high_churn", "slow_review"}


@pytest.mark.asyncio
async def test_tenant_settings_creation(test_tenant_settings, test_tenant):
    """Verify tenant settings were created."""
    assert test_tenant_settings.tenant_id == test_tenant.id
    assert test_tenant_settings.analysis_window_days == 7
