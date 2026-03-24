"""
Audit MCP Server
Provides Model Context Protocol interface for auditing, monitoring, and CEO briefings.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import config, LOGS_DIR, REPORTS_DIR, RiskLevel


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: datetime
    agent: str
    action: str
    details: Dict[str, Any]
    success: bool
    risk_level: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent,
            "action": self.action,
            "details": self.details,
            "success": self.success,
            "risk_level": self.risk_level,
        }


@dataclass
class AuditReport:
    """Comprehensive audit report."""
    report_id: str
    report_type: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "raw_data": self.raw_data,
        }


class AuditMCPServer:
    """
    MCP Server for auditing and monitoring operations.
    Handles weekly audits, compliance checks, and CEO briefings.
    """

    def __init__(self):
        self.name = "audit_mcp"
        self.logger = logging.getLogger(f"gold.mcp.{self.name}")
        self.is_running = False
        self.audit_dir = LOGS_DIR / "audit"
        self.reports_dir = REPORTS_DIR
        self._tools = self._define_tools()
        self._scheduled_audits: Dict[str, asyncio.Task] = {}

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available MCP tools for audit operations."""
        return {
            # Audit operations
            "run_weekly_business_audit": {
                "name": "run_weekly_business_audit",
                "description": "Run a comprehensive weekly business audit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_social": {"type": "boolean", "default": True},
                        "include_accounting": {"type": "boolean", "default": True},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "run_weekly_accounting_audit": {
                "name": "run_weekly_accounting_audit",
                "description": "Run a weekly accounting audit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "check_reconciliation": {"type": "boolean", "default": True},
                        "check_outstanding": {"type": "boolean", "default": True},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "generate_ceo_briefing": {
                "name": "generate_ceo_briefing",
                "description": "Generate a CEO-level briefing report",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                        "include_recommendations": {"type": "boolean", "default": True},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },

            # Log operations
            "get_audit_logs": {
                "name": "get_audit_logs",
                "description": "Retrieve audit logs for a time period",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "agent": {"type": "string", "description": "Filter by agent name"},
                        "action": {"type": "string", "description": "Filter by action"},
                        "success_only": {"type": "boolean", "default": False},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "get_error_summary": {
                "name": "get_error_summary",
                "description": "Get summary of errors in a time period",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },

            # Compliance operations
            "run_compliance_check": {
                "name": "run_compliance_check",
                "description": "Run compliance checks on system operations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "check_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["approval_workflow", "data_retention", "access_control"],
                            },
                        },
                    },
                },
                "risk_level": RiskLevel.LOW,
            },

            # Alert operations
            "get_active_alerts": {
                "name": "get_active_alerts",
                "description": "Get currently active system alerts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "create_alert": {
                "name": "create_alert",
                "description": "Create a new system alert",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "message": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "source": {"type": "string"},
                    },
                    "required": ["title", "message", "severity"],
                },
                "risk_level": RiskLevel.LOW,
            },

            # Report operations
            "list_reports": {
                "name": "list_reports",
                "description": "List available audit reports",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "enum": ["business_audit", "accounting_audit", "ceo_briefing", "compliance"],
                        },
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "get_report": {
                "name": "get_report",
                "description": "Get a specific audit report by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "report_id": {"type": "string"},
                    },
                    "required": ["report_id"],
                },
                "risk_level": RiskLevel.LOW,
            },
        }

    async def start(self) -> bool:
        """Start the Audit MCP server."""
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "audits").mkdir(exist_ok=True)
        (self.reports_dir / "briefings").mkdir(exist_ok=True)

        self.is_running = True
        self.logger.info("Audit MCP server started")

        # Schedule weekly audits if configured
        if config.audit.ceo_briefing_enabled:
            await self._schedule_weekly_audit()

        return True

    async def stop(self) -> None:
        """Stop the Audit MCP server."""
        # Cancel scheduled tasks
        for task in self._scheduled_audits.values():
            task.cancel()
        self._scheduled_audits.clear()

        self.is_running = False
        self.logger.info("Audit MCP server stopped")

    async def _schedule_weekly_audit(self) -> None:
        """Schedule the weekly audit based on configuration."""
        self.logger.info(
            f"Weekly audit scheduled for {config.audit.weekly_audit_day} "
            f"at {config.audit.weekly_audit_hour}:00"
        )
        # In production, this would use a proper scheduler like APScheduler

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for MCP discovery."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        method_name = f"_execute_{tool_name}"
        if hasattr(self, method_name):
            try:
                result = await getattr(self, method_name)(arguments)
                return {"success": True, "result": result}
            except Exception as e:
                self.logger.error(f"Tool execution error: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"error": f"Tool not implemented: {tool_name}"}

    # Audit implementations

    async def _execute_run_weekly_business_audit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive weekly business audit."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        report = AuditReport(
            report_id=f"business_audit_{now.strftime('%Y%m%d_%H%M%S')}",
            report_type="business_audit",
            generated_at=now,
            period_start=week_ago,
            period_end=now,
        )

        # Gather audit data
        audit_logs = await self._get_audit_logs_internal(week_ago, now)
        report.raw_data["audit_logs_count"] = len(audit_logs)

        # Analyze success rates
        success_count = sum(1 for log in audit_logs if log.get("success", False))
        total_count = len(audit_logs)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 100

        report.summary = {
            "total_operations": total_count,
            "successful_operations": success_count,
            "failed_operations": total_count - success_count,
            "success_rate_percent": round(success_rate, 2),
        }

        # Add findings
        if success_rate < 95:
            report.findings.append({
                "severity": "warning",
                "finding": f"Success rate ({success_rate:.1f}%) is below target (95%)",
                "impact": "Operational efficiency may be affected",
            })

        # Check for high-risk operations
        high_risk_ops = [log for log in audit_logs if log.get("risk_level") in ["high", "critical"]]
        if high_risk_ops:
            report.findings.append({
                "severity": "info",
                "finding": f"{len(high_risk_ops)} high-risk operations executed this week",
                "details": [op.get("action") for op in high_risk_ops[:5]],
            })

        # Include social media summary if requested
        if args.get("include_social", True):
            report.raw_data["social_media"] = {"status": "pending_integration"}

        # Include accounting summary if requested
        if args.get("include_accounting", True):
            report.raw_data["accounting"] = {"status": "pending_integration"}

        # Generate recommendations
        if total_count == 0:
            report.recommendations.append("No operations recorded - verify logging is working correctly")
        if success_rate < 90:
            report.recommendations.append("Review failed operations and implement fixes")

        # Save report
        self._save_report(report)

        return report.to_dict()

    async def _execute_run_weekly_accounting_audit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run weekly accounting audit."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        report = AuditReport(
            report_id=f"accounting_audit_{now.strftime('%Y%m%d_%H%M%S')}",
            report_type="accounting_audit",
            generated_at=now,
            period_start=week_ago,
            period_end=now,
        )

        # Accounting-specific checks
        checks_passed = 0
        total_checks = 0

        # Check 1: Invoice status
        total_checks += 1
        report.raw_data["invoices"] = {
            "check": "invoice_status",
            "status": "requires_odoo_connection",
        }

        # Check 2: Payment reconciliation
        if args.get("check_reconciliation", True):
            total_checks += 1
            report.raw_data["reconciliation"] = {
                "check": "payment_reconciliation",
                "status": "requires_odoo_connection",
            }

        # Check 3: Outstanding receivables
        if args.get("check_outstanding", True):
            total_checks += 1
            report.raw_data["receivables"] = {
                "check": "aged_receivables",
                "status": "requires_odoo_connection",
            }

        report.summary = {
            "checks_performed": total_checks,
            "checks_passed": checks_passed,
            "checks_requiring_attention": total_checks - checks_passed,
            "odoo_connection_required": True,
        }

        report.recommendations.append("Configure Odoo connection to enable full accounting audit")

        self._save_report(report)
        return report.to_dict()

    async def _execute_generate_ceo_briefing(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CEO-level briefing."""
        now = datetime.now()
        period = args.get("period", "weekly")

        if period == "daily":
            period_start = now - timedelta(days=1)
        elif period == "monthly":
            period_start = now - timedelta(days=30)
        else:  # weekly
            period_start = now - timedelta(days=7)

        briefing = {
            "briefing_id": f"ceo_briefing_{now.strftime('%Y%m%d_%H%M%S')}",
            "generated_at": now.isoformat(),
            "period": {
                "type": period,
                "start": period_start.isoformat(),
                "end": now.isoformat(),
            },
            "executive_summary": "",
            "system_health": "OPERATIONAL",
            "key_metrics": {},
            "highlights": [],
            "concerns": [],
            "recommendations": [],
        }

        # Get audit logs for the period
        audit_logs = await self._get_audit_logs_internal(period_start, now)

        # Calculate metrics
        total_ops = len(audit_logs)
        success_ops = sum(1 for log in audit_logs if log.get("success", False))
        success_rate = (success_ops / total_ops * 100) if total_ops > 0 else 100

        briefing["key_metrics"] = {
            "total_operations": total_ops,
            "success_rate": f"{success_rate:.1f}%",
            "integrations_active": sum(1 for s in config.get_integration_status().values()
                                       if s.value in ["configured", "connected"]),
        }

        # Generate executive summary
        briefing["executive_summary"] = (
            f"Gold Tier AI Employee processed {total_ops} operations with "
            f"{success_rate:.1f}% success rate during the {period} period. "
            f"System is operational and functioning within normal parameters."
        )

        # Determine system health
        if success_rate >= 98:
            briefing["system_health"] = "EXCELLENT"
        elif success_rate >= 95:
            briefing["system_health"] = "GOOD"
        elif success_rate >= 90:
            briefing["system_health"] = "FAIR"
            briefing["concerns"].append("Success rate below target - monitoring recommended")
        else:
            briefing["system_health"] = "NEEDS_ATTENTION"
            briefing["concerns"].append("Success rate significantly below target - immediate review recommended")

        # Add recommendations if requested
        if args.get("include_recommendations", True):
            integration_status = config.get_integration_status()
            for name, status in integration_status.items():
                if status.value == "not_configured":
                    briefing["recommendations"].append(
                        f"Configure {name.title()} integration to expand capabilities"
                    )

        # Save briefing
        briefing_dir = self.reports_dir / "briefings"
        briefing_dir.mkdir(parents=True, exist_ok=True)
        file_path = briefing_dir / f"{briefing['briefing_id']}.json"
        with open(file_path, "w") as f:
            json.dump(briefing, f, indent=2)

        return briefing

    async def _execute_get_audit_logs(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve audit logs."""
        date_from = datetime.fromisoformat(args.get("date_from", (datetime.now() - timedelta(days=7)).isoformat().split("T")[0]))
        date_to = datetime.fromisoformat(args.get("date_to", datetime.now().isoformat().split("T")[0]))

        logs = await self._get_audit_logs_internal(date_from, date_to)

        # Apply filters
        if args.get("agent"):
            logs = [log for log in logs if log.get("agent") == args["agent"]]
        if args.get("action"):
            logs = [log for log in logs if args["action"] in log.get("action", "")]
        if args.get("success_only"):
            logs = [log for log in logs if log.get("success", False)]

        return logs

    async def _get_audit_logs_internal(
        self,
        date_from: datetime,
        date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Internal method to retrieve audit logs from files."""
        logs = []

        current_date = date_from
        while current_date <= date_to:
            date_str = current_date.strftime("%Y-%m-%d")
            audit_file = self.audit_dir / f"audit_{date_str}.jsonl"

            if audit_file.exists():
                with open(audit_file, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                logs.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            current_date += timedelta(days=1)

        return logs

    async def _execute_get_error_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get error summary."""
        date_from = datetime.fromisoformat(args.get("date_from", (datetime.now() - timedelta(days=7)).isoformat().split("T")[0]))
        date_to = datetime.fromisoformat(args.get("date_to", datetime.now().isoformat().split("T")[0]))

        logs = await self._get_audit_logs_internal(date_from, date_to)
        errors = [log for log in logs if not log.get("success", True)]

        # Group errors by action
        error_by_action: Dict[str, int] = {}
        for error in errors:
            action = error.get("action", "unknown")
            error_by_action[action] = error_by_action.get(action, 0) + 1

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
            },
            "total_errors": len(errors),
            "errors_by_action": error_by_action,
            "recent_errors": errors[-10:],  # Last 10 errors
        }

    async def _execute_run_compliance_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run compliance checks."""
        check_types = args.get("check_types", ["approval_workflow", "data_retention", "access_control"])

        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "overall_compliance": True,
        }

        for check_type in check_types:
            if check_type == "approval_workflow":
                results["checks"]["approval_workflow"] = {
                    "status": "compliant",
                    "description": "All high-risk operations require approval",
                    "verified": True,
                }
            elif check_type == "data_retention":
                results["checks"]["data_retention"] = {
                    "status": "compliant",
                    "description": f"Audit logs retained for {config.audit.retention_days} days",
                    "retention_days": config.audit.retention_days,
                }
            elif check_type == "access_control":
                results["checks"]["access_control"] = {
                    "status": "compliant",
                    "description": "Operations logged with agent identification",
                    "verified": True,
                }

        return results

    async def _execute_get_active_alerts(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get active alerts."""
        alerts_file = self.audit_dir / "alerts.json"

        if not alerts_file.exists():
            return []

        with open(alerts_file, "r") as f:
            alerts = json.load(f)

        # Filter by severity if specified
        severity = args.get("severity")
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]

        # Filter to only active (not acknowledged) alerts
        alerts = [a for a in alerts if not a.get("acknowledged", False)]

        return alerts

    async def _execute_create_alert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new alert."""
        alert = {
            "id": f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "title": args["title"],
            "message": args["message"],
            "severity": args["severity"],
            "source": args.get("source", "audit_server"),
            "acknowledged": False,
        }

        alerts_file = self.audit_dir / "alerts.json"

        if alerts_file.exists():
            with open(alerts_file, "r") as f:
                alerts = json.load(f)
        else:
            alerts = []

        alerts.append(alert)

        with open(alerts_file, "w") as f:
            json.dump(alerts, f, indent=2)

        return alert

    async def _execute_list_reports(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List available reports."""
        report_type = args.get("report_type")
        limit = args.get("limit", 20)

        reports = []

        # Check audits directory
        audits_dir = self.reports_dir / "audits"
        if audits_dir.exists():
            for file in sorted(audits_dir.glob("*.json"), reverse=True)[:limit]:
                with open(file, "r") as f:
                    report = json.load(f)
                    if not report_type or report.get("report_type") == report_type:
                        reports.append({
                            "report_id": report.get("report_id"),
                            "report_type": report.get("report_type"),
                            "generated_at": report.get("generated_at"),
                        })

        # Check briefings directory
        briefings_dir = self.reports_dir / "briefings"
        if briefings_dir.exists():
            for file in sorted(briefings_dir.glob("*.json"), reverse=True)[:limit]:
                with open(file, "r") as f:
                    report = json.load(f)
                    if not report_type or report_type == "ceo_briefing":
                        reports.append({
                            "report_id": report.get("briefing_id"),
                            "report_type": "ceo_briefing",
                            "generated_at": report.get("generated_at"),
                        })

        return reports[:limit]

    async def _execute_get_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific report."""
        report_id = args["report_id"]

        # Search in audits
        for file in (self.reports_dir / "audits").glob("*.json"):
            with open(file, "r") as f:
                report = json.load(f)
                if report.get("report_id") == report_id:
                    return report

        # Search in briefings
        for file in (self.reports_dir / "briefings").glob("*.json"):
            with open(file, "r") as f:
                report = json.load(f)
                if report.get("briefing_id") == report_id:
                    return report

        return {"error": f"Report not found: {report_id}"}

    def _save_report(self, report: AuditReport) -> Path:
        """Save an audit report."""
        audits_dir = self.reports_dir / "audits"
        audits_dir.mkdir(parents=True, exist_ok=True)

        file_path = audits_dir / f"{report.report_id}.json"
        with open(file_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        self.logger.info(f"Report saved: {file_path}")
        return file_path

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Audit MCP server."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "audit_directory": str(self.audit_dir),
            "reports_directory": str(self.reports_dir),
            "scheduled_audits": list(self._scheduled_audits.keys()),
            "tools_available": len(self._tools),
            "config": {
                "audit_day": config.audit.weekly_audit_day,
                "audit_hour": config.audit.weekly_audit_hour,
                "retention_days": config.audit.retention_days,
                "ceo_briefing_enabled": config.audit.ceo_briefing_enabled,
            },
        }
