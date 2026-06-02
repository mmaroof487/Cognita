"""
Seed a demo tenant, user, and generate a valid JWT access token.
Usage: docker compose exec -T api python scripts/seed_demo_token.py
"""

import asyncio
import uuid
import os
import sys

# Add /app to sys.path so it can find 'app' module
sys.path.append("/app")

from app.database import async_session_factory
from app.models import Tenant, TenantSettings, User
from app.core.security import create_access_token

async def main():
    async with async_session_factory() as session:
        # Create Demo Tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Demo Corp",
            github_org="demo_org"
        )
        session.add(tenant)
        
        # Create Tenant Settings
        settings = TenantSettings(
            tenant_id=tenant_id,
            analysis_window_days=7
        )
        session.add(settings)
        
        # Create Admin User (bypassing github OAuth)
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            github_id=999999999,  # dummy
            github_login="demo_admin",
            email="admin@democorp.com",
            role="owner"
        )
        session.add(user)
        
        await session.commit()
        
        from app.models import Org, Insight, AgentRun, AgentAction
        from datetime import datetime, timezone

        org_id = uuid.uuid4()
        org = Org(
            id=org_id,
            tenant_id=tenant_id,
            github_org="demo_org_repo",
            display_name="Demo Organization"
        )
        session.add(org)

        run_id = uuid.uuid4()
        run = AgentRun(
            id=run_id,
            tenant_id=tenant_id,
            org_id=org_id,
            repo_id=None,
            agent_type="analyst",
            status="completed"
        )
        session.add(run)

        insight_id = uuid.uuid4()
        insight = Insight(
            id=insight_id,
            tenant_id=tenant_id,
            org_id=org_id,
            repo_id=None,
            insight_type="burnout_risk",
            severity="high",
            title="Burnout Risk Detected",
            description="Alice has been committing code over the last 3 weekends.",
            agent_run_id=run_id
        )
        session.add(insight)

        action_id = uuid.uuid4()
        action = AgentAction(
            id=action_id,
            tenant_id=tenant_id,
            agent_run_id=run_id,
            insight_id=insight_id,
            action_type="send_slack",
            status="pending",
            payload={"channel": "#engineering-alerts", "message": "Burnout risk for Alice"}
        )
        session.add(action)

        await session.commit()
        
        # Generate JWT Token
        token_data = {
            "sub": str(user_id), 
            "tenant_id": str(tenant_id), 
            "role": "owner"
        }
        access_token = create_access_token(token_data)
        
        print("\n=========================================")
        print(" Seed Complete! ")
        print(f" Tenant ID: {tenant_id}")
        print(f" Org ID:    {org_id}")
        print(f" User ID:   {user_id}")
        print("\n --- YOUR JWT ACCESS TOKEN --- ")
        print(access_token)
        print("=========================================\n")
        print("To use this in Swagger UI (http://localhost:8000/docs):")
        print("1. Click the 'Authorize' button.")
        print("2. Enter the token above in the value field.")
        print("3. Click 'Authorize'.")

if __name__ == "__main__":
    asyncio.run(main())
