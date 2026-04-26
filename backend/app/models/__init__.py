"""
ORM Models package.
All models inherit from Base for Alembic to auto-detect them.
"""

from app.models.base import Base, BaseModel
from app.models.tenant import Tenant
from app.models.user import User
from app.models.org import Org
from app.models.repo import Repo
from app.models.developer import Developer
from app.models.commit_event import CommitEvent
from app.models.pr_event import PrEvent
from app.models.insight import Insight
from app.models.agent_run import AgentRun
from app.models.agent_action import AgentAction
from app.models.audit_log import AuditLog
from app.models.tenant_settings import TenantSettings
from app.models.jira_template import JiraTemplate

__all__ = [
    "Base",
    "BaseModel",
    "Tenant",
    "User",
    "Org",
    "Repo",
    "Developer",
    "CommitEvent",
    "PrEvent",
    "Insight",
    "AgentRun",
    "AgentAction",
    "AuditLog",
    "TenantSettings",
    "JiraTemplate",
]
