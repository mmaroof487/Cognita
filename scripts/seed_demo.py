"""
Seed the production database with a demo tenant and API key.
Usage: docker compose -f docker-compose.prod.yml exec -T api python scripts/seed_demo.py
"""

import asyncio
import uuid
import secrets
from app.database import async_session_factory
from app.models import Tenant, TenantSettings, User
from app.core.security import get_password_hash

async def main():
    print("Seeding demo data...")
    async with async_session_factory() as session:
        # Create Demo Tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Demo Corp",
        )
        session.add(tenant)
        
        # Create Tenant Settings
        settings = TenantSettings(
            tenant_id=tenant_id,
            analysis_window_days=7
        )
        session.add(settings)
        
        # Create Admin User
        admin_pass = secrets.token_urlsafe(12)
        admin_email = "admin@democorp.com"
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=admin_email,
            hashed_password=get_password_hash(admin_pass),
            is_active=True,
            is_superuser=True
        )
        session.add(admin)
        
        await session.commit()
        
        print("\n=========================================")
        print(" Seed Complete! ")
        print(f" Tenant ID: {tenant_id}")
        print(f" Admin Email: {admin_email}")
        print(f" Admin Password: {admin_pass}")
        print(" IMPORTANT: Save these credentials now.")
        print("=========================================\n")

if __name__ == "__main__":
    asyncio.run(main())
