import asyncio
import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import sys
import os

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session_factory
from app.models.tenant import Tenant
from app.models.org import Org
from app.models.user import User
from app.core.security import create_access_token
from app.config import settings

async def wipe_db(db: AsyncSession):
    # Disable foreign key checks for dropping data
    await db.execute(text("TRUNCATE TABLE agent_actions, insights, agent_runs, audit_logs, pr_events, commit_events, developers, repos, orgs, users, tenants RESTART IDENTITY CASCADE;"))
    await db.commit()

async def setup():
    async with async_session_factory() as db:
        print("Wiping existing data...")
        await wipe_db(db)
        
        print("Creating default tenant...")
        tenant = Tenant(
            id=uuid.uuid4(),
            name="My Workspace"
        )
        db.add(tenant)
        
        print("Creating admin user...")
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            github_id=12345678,
            github_login="admin",
            email="admin@cognita.local",
            role="owner"
        )
        db.add(user)
        
        org_name = sys.argv[1] if len(sys.argv) > 1 else "MyOrg"
        print(f"Creating GitHub organization: {org_name}...")
        org = Org(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=org_name,
            github_installation_id="12345" # Dummy
        )
        db.add(org)
        
        await db.commit()
        
        jwt_token = create_access_token(
            data={"sub": str(user.id), "tenant_id": str(tenant.id)}
        )
        
        print("\n=== SETUP COMPLETE ===")
        print("Please log out from the frontend and use these new credentials:")
        print(f"JWT Access Token: {jwt_token}")
        print(f"Organization ID:  {org.id}")

if __name__ == "__main__":
    asyncio.run(setup())
