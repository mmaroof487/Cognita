import httpx
import smtplib
from email.message import EmailMessage
from app.models import TenantSettings, JiraTemplate
from app.core.security import fernet_decrypt
from typing import Optional

async def send_slack(settings: TenantSettings, payload: dict) -> None:
    if not settings.slack_webhook_url:
        return
    webhook_url = fernet_decrypt(settings.slack_webhook_url)
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={"text": payload.get("message", "Axon Alert")})

async def send_email(settings: TenantSettings, payload: dict) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password or not settings.notification_email:
        return
        
    password = fernet_decrypt(settings.smtp_password)
    msg = EmailMessage()
    msg.set_content(payload.get("message", "Axon Alert"))
    msg["Subject"] = payload.get("subject", "Axon Alert")
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notification_email
    
    port = settings.smtp_port or 587
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        def _send():
            with smtplib.SMTP(settings.smtp_host, port) as server:
                server.starttls()
                server.login(settings.smtp_user, password)
                server.send_message(msg)
        await loop.run_in_executor(None, _send)
    except Exception as e:
        print(f"Error sending email: {e}")

async def create_jira_ticket(settings: TenantSettings, payload: dict, template: JiraTemplate) -> Optional[str]:
    from app.config import settings as app_settings
    
    jira_url = getattr(settings, "jira_base_url", getattr(app_settings, "jira_base_url", None))
    user = getattr(settings, "jira_api_user", getattr(app_settings, "jira_api_user", None))
    token = getattr(settings, "jira_api_token", getattr(app_settings, "jira_api_token", None))
    project_key = getattr(settings, "jira_project_key", getattr(app_settings, "jira_project_key", None))
    
    if not jira_url or not user or not token or not project_key:
        return None
        
    token_plain = fernet_decrypt(token) if hasattr(settings, "jira_api_token") and settings.jira_api_token else token
    
    auth = (user, token_plain)
    
    summary = template.summary_template.format(**payload)
    description = template.description_template.format(**payload)
    
    issue_data = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"text": description, "type": "text"}
                        ]
                    }
                ]
            },
            "issuetype": {"name": template.issue_type},
            "labels": template.labels
        }
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{jira_url.rstrip('/')}/rest/api/3/issue", json=issue_data, auth=auth)
        if res.status_code == 201:
            return res.json().get("key")
    return None
