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
    await db.execute(text("TRUNCATE TABLE tenants CASCADE;"))
    await db.commit()

async def setup():
    async with async_session_factory() as db:
        print("Wiping existing data...")
        await wipe_db(db)
        
        print("Creating default tenant...")
        org_name = sys.argv[1] if len(sys.argv) > 1 else "MyOrg"
        tenant = Tenant(
            id=uuid.uuid4(),
            name="My Workspace",
            github_org=org_name
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
            github_org=org_name,
            display_name=org_name
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
