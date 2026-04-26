"""
Test configuration and fixtures.
Provides: async_session_factory, test_tenant, test_user, async db, test client.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient
from datetime import datetime, timezone
import uuid

# Import models
from app.models import Base, Tenant, User, TenantSettings, JiraTemplate
from app.main import app
from app.database import get_async_session


# ─────────────────────────────────────────────────────────────────────────────
# Test Database Setup
# ─────────────────────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "postgresql+asyncpg://devpulse:devpulse@localhost:5432/devpulse_test"


@pytest_asyncio.fixture
async def test_engine():
    """Create an async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session_factory(test_engine):
    """Create async session factory for tests."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def test_session(async_session_factory):
    """Provide an async database session for a test."""
    async with async_session_factory() as session:
        yield session


# ─────────────────────────────────────────────────────────────────────────────
# Test Tenant & User Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_tenant(test_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant",
        github_org="test-org",
        plan="enterprise",
        rate_limit_per_min=1000,
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        github_id=123456789,
        github_login="test-user",
        email="test@example.com",
        role="owner",
        access_token="encrypted:test-token-dev",
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_tenant_settings(test_session: AsyncSession, test_tenant: Tenant) -> TenantSettings:
    """Create tenant settings."""
    settings = TenantSettings(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        analysis_window_days=7,
    )
    test_session.add(settings)
    await test_session.commit()
    await test_session.refresh(settings)
    return settings


@pytest_asyncio.fixture
async def test_jira_templates(test_session: AsyncSession, test_tenant: Tenant) -> list[JiraTemplate]:
    """Create default Jira templates."""
    templates = [
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            anomaly_type="burnout_risk",
            summary_template="[DevPulse] Burnout Risk: {developer_login}",
            description_template="Burnout risk detected for {developer_login}",
            issue_type="Task",
            priority_default="High",
            labels=["devpulse", "burnout-risk"],
        ),
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            anomaly_type="high_churn",
            summary_template="[DevPulse] High Churn: {developer_login}",
            description_template="High code churn from {developer_login}",
            issue_type="Task",
            priority_default="Medium",
            labels=["devpulse", "code-quality"],
        ),
        JiraTemplate(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            anomaly_type="slow_review",
            summary_template="[DevPulse] Slow Review: {developer_login}",
            description_template="Slow review cycle for {developer_login}",
            issue_type="Task",
            priority_default="Medium",
            labels=["devpulse", "review-process"],
        ),
    ]
    for t in templates:
        test_session.add(t)
    await test_session.commit()
    for t in templates:
        await test_session.refresh(t)
    return templates


# ─────────────────────────────────────────────────────────────────────────────
# Test Client Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_client(async_session_factory):
    """Provide an AsyncClient for testing endpoints."""

    async def override_get_async_session():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
