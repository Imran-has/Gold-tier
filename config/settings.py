"""
Gold Tier Configuration Settings
Central configuration for all Gold tier components.
"""

import os
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
EVENTS_DIR = BASE_DIR / "events"
PLANS_DIR = BASE_DIR / "plans"
REPORTS_DIR = BASE_DIR / "reports"
CREDENTIALS_DIR = CONFIG_DIR / "credentials"


class RiskLevel(Enum):
    """Risk levels for operations requiring approval."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntegrationStatus(Enum):
    """Status of external integrations."""
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class OdooConfig:
    """Odoo Community server configuration."""
    url: str = os.getenv("ODOO_URL", "http://localhost:8069")
    database: str = os.getenv("ODOO_DATABASE", "odoo")
    username: str = os.getenv("ODOO_USERNAME", "admin")
    password: str = os.getenv("ODOO_PASSWORD", "")
    timeout: int = int(os.getenv("ODOO_TIMEOUT", "30"))

    def is_configured(self) -> bool:
        return bool(self.url and self.database and self.username and self.password)


@dataclass
class FacebookConfig:
    """Facebook/Meta API configuration."""
    app_id: str = os.getenv("FACEBOOK_APP_ID", "")
    app_secret: str = os.getenv("FACEBOOK_APP_SECRET", "")
    access_token: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    page_id: str = os.getenv("FACEBOOK_PAGE_ID", "")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.page_id)


@dataclass
class InstagramConfig:
    """Instagram API configuration (via Facebook Graph API)."""
    access_token: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    business_account_id: str = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.business_account_id)


@dataclass
class TwitterConfig:
    """Twitter/X API configuration."""
    api_key: str = os.getenv("TWITTER_API_KEY", "")
    api_secret: str = os.getenv("TWITTER_API_SECRET", "")
    access_token: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    access_token_secret: str = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
    bearer_token: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token)


@dataclass
class LinkedInConfig:
    """LinkedIn API configuration."""
    client_id: str = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    access_token: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    organization_id: str = os.getenv("LINKEDIN_ORGANIZATION_ID", "")  # For company pages

    def is_configured(self) -> bool:
        return bool(self.access_token)


@dataclass
class AuditConfig:
    """Audit and monitoring configuration."""
    weekly_audit_day: str = os.getenv("AUDIT_DAY", "sunday")  # Day of week
    weekly_audit_hour: int = int(os.getenv("AUDIT_HOUR", "9"))  # Hour in 24h format
    retention_days: int = int(os.getenv("AUDIT_RETENTION_DAYS", "90"))
    ceo_briefing_enabled: bool = os.getenv("CEO_BRIEFING_ENABLED", "true").lower() == "true"


@dataclass
class RalphLoopConfig:
    """Ralph Wiggum Loop configuration."""
    max_retries: int = int(os.getenv("RALPH_MAX_RETRIES", "3"))
    retry_delay_seconds: int = int(os.getenv("RALPH_RETRY_DELAY", "5"))
    verification_timeout: int = int(os.getenv("RALPH_VERIFY_TIMEOUT", "60"))
    enable_learning: bool = os.getenv("RALPH_ENABLE_LEARNING", "true").lower() == "true"


@dataclass
class MCPServerConfig:
    """MCP Server configuration."""
    odoo_port: int = int(os.getenv("MCP_ODOO_PORT", "8766"))
    social_port: int = int(os.getenv("MCP_SOCIAL_PORT", "8767"))
    audit_port: int = int(os.getenv("MCP_AUDIT_PORT", "8768"))
    host: str = os.getenv("MCP_HOST", "localhost")


@dataclass
class GoldConfig:
    """Main Gold tier configuration."""
    odoo: OdooConfig = field(default_factory=OdooConfig)
    facebook: FacebookConfig = field(default_factory=FacebookConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    linkedin: LinkedInConfig = field(default_factory=LinkedInConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    ralph_loop: RalphLoopConfig = field(default_factory=RalphLoopConfig)
    mcp_servers: MCPServerConfig = field(default_factory=MCPServerConfig)

    # Logging
    log_level: str = os.getenv("GOLD_LOG_LEVEL", "INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Claude AI
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    def get_integration_status(self) -> Dict[str, IntegrationStatus]:
        """Get status of all integrations."""
        return {
            "odoo": IntegrationStatus.CONFIGURED if self.odoo.is_configured() else IntegrationStatus.NOT_CONFIGURED,
            "facebook": IntegrationStatus.CONFIGURED if self.facebook.is_configured() else IntegrationStatus.NOT_CONFIGURED,
            "instagram": IntegrationStatus.CONFIGURED if self.instagram.is_configured() else IntegrationStatus.NOT_CONFIGURED,
            "twitter": IntegrationStatus.CONFIGURED if self.twitter.is_configured() else IntegrationStatus.NOT_CONFIGURED,
            "linkedin": IntegrationStatus.CONFIGURED if self.linkedin.is_configured() else IntegrationStatus.NOT_CONFIGURED,
            "anthropic": IntegrationStatus.CONFIGURED if self.anthropic_api_key else IntegrationStatus.NOT_CONFIGURED,
        }


# Global configuration instance
config = GoldConfig()


# Risk level mappings for operations
OPERATION_RISK_LEVELS = {
    # Odoo operations
    "odoo.read": RiskLevel.LOW,
    "odoo.search": RiskLevel.LOW,
    "odoo.list_invoices": RiskLevel.LOW,
    "odoo.get_invoice": RiskLevel.LOW,
    "odoo.list_partners": RiskLevel.LOW,
    "odoo.list_expenses": RiskLevel.LOW,
    "odoo.list_journal_entries": RiskLevel.LOW,
    "odoo.get_profit_loss": RiskLevel.LOW,
    "odoo.get_balance_sheet": RiskLevel.LOW,
    "odoo.get_aged_receivables": RiskLevel.LOW,
    "odoo.create_invoice": RiskLevel.MEDIUM,
    "odoo.create_draft_invoice": RiskLevel.MEDIUM,
    "odoo.create_partner": RiskLevel.MEDIUM,
    "odoo.create_expense": RiskLevel.MEDIUM,
    "odoo.send_invoice": RiskLevel.HIGH,
    "odoo.create_payment": RiskLevel.HIGH,
    "odoo.delete": RiskLevel.CRITICAL,

    # Social media operations
    "social.read_analytics": RiskLevel.LOW,
    "social.draft_post": RiskLevel.LOW,
    "social.publish_post": RiskLevel.MEDIUM,
    "social.delete_post": RiskLevel.HIGH,
    "social.bulk_action": RiskLevel.CRITICAL,

    # Audit operations
    "audit.generate_report": RiskLevel.LOW,
    "audit.ceo_briefing": RiskLevel.LOW,
    "audit.compliance_check": RiskLevel.LOW,
}


def get_operation_risk(operation: str) -> RiskLevel:
    """Get the risk level for an operation."""
    return OPERATION_RISK_LEVELS.get(operation, RiskLevel.MEDIUM)


def requires_approval(operation: str) -> bool:
    """Check if an operation requires human approval."""
    risk = get_operation_risk(operation)
    return risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
